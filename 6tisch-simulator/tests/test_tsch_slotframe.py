"""
Test for TSCH Slotframe and Cell manipulation
"""
from __future__ import print_function
from __future__ import absolute_import

from builtins import str
from builtins import range
import random

import pytest

from . import test_utils as u
from SimEngine.Mote.tsch import SlotFrame, Cell
from SimEngine import SimLog
from SimEngine.Mote import Mote
import SimEngine.Mote.MoteDefines as d

all_options_on = [d.CELLOPTION_TX, d.CELLOPTION_RX, d.CELLOPTION_SHARED]

@pytest.fixture(params=[None, 'test_mac_addr'])
def fixture_neighbor_mac_addr(request):
    return request.param


def test_add(sim_engine, fixture_neighbor_mac_addr):
    sim_engine = sim_engine() # need for log

    slotframe = SlotFrame(None, 1, 101)
    cell = Cell(0, 0, all_options_on, fixture_neighbor_mac_addr)
    slotframe.add(cell)

    assert slotframe.get_cells_at_asn(0) == [cell]
    assert slotframe.get_cells_at_asn(1) == []
    assert slotframe.get_cells_at_asn(100) == []
    assert slotframe.get_cells_at_asn(101) == [cell]

    assert slotframe.get_cells_by_slot_offset(0) == [cell]
    assert slotframe.get_cells_by_slot_offset(1) == []
    assert slotframe.get_cells_by_slot_offset(100) == []

    assert slotframe.get_cells_by_mac_addr(fixture_neighbor_mac_addr) == [cell]
    assert slotframe.get_cells_by_mac_addr('dummy_mac_addr') == []

    assert (
        [cell for cell in slotframe.get_cells_by_mac_addr(fixture_neighbor_mac_addr) if cell.options == [d.CELLOPTION_TX, d.CELLOPTION_RX, d.CELLOPTION_SHARED]] == [cell]
    )


def test_delete_cell(sim_engine):
    sim_engine = sim_engine() # need for log

    neighbor_mac_addr = 'test_mac_addr'
    slotframe = SlotFrame(None, 1, 101)
    cell = Cell(0, 0, all_options_on, neighbor_mac_addr)

    assert slotframe.get_cells_by_mac_addr(neighbor_mac_addr) == []
    assert slotframe.get_cells_by_slot_offset(0) == []

    slotframe.add(cell)

    assert slotframe.get_cells_by_mac_addr(neighbor_mac_addr) == [cell]
    assert slotframe.get_cells_by_slot_offset(0) == [cell]

    slotframe.delete(cell)

    assert slotframe.get_cells_by_mac_addr(neighbor_mac_addr) == []
    assert slotframe.get_cells_by_slot_offset(0) == []


def test_add_cells_for_same_mac_addr(sim_engine):
    sim_engine = sim_engine() # need for log

    slotframe = SlotFrame(None, 1, 101)

    cell_1 = Cell(1, 5, [d.CELLOPTION_TX], 'test_mac_addr_1')
    cell_2 = Cell(51, 10, [d.CELLOPTION_RX], 'test_mac_addr_1')

    assert slotframe.get_cells_by_slot_offset(1) == []

    slotframe.add(cell_1)
    slotframe.add(cell_2)

    assert slotframe.get_cells_by_slot_offset(1) == [cell_1]
    assert slotframe.get_cells_by_slot_offset(51) == [cell_2]
    assert slotframe.get_cells_by_mac_addr('test_mac_addr_1') == [
        cell_1, cell_2
    ]


def test_add_cells_at_same_slot_offset(sim_engine):
    sim_engine = sim_engine() # need for log

    slotframe = SlotFrame(None, 1, 101)

    cell_1 = Cell(1, 5, [d.CELLOPTION_TX], 'test_mac_addr_1')
    cell_2 = Cell(1, 5, [d.CELLOPTION_RX], 'test_mac_addr_2')

    assert slotframe.get_cells_by_slot_offset(1) == []

    slotframe.add(cell_1)
    slotframe.add(cell_2)

    assert slotframe.get_cells_by_slot_offset(1) == [
        cell_1, cell_2
    ]
    assert slotframe.get_cells_by_mac_addr('test_mac_addr_1') == [cell_1]
    assert slotframe.get_cells_by_mac_addr('test_mac_addr_2') == [cell_2]

    slotframe.delete(cell_1)

    assert slotframe.get_cells_by_mac_addr('test_mac_addr_1') == []
    assert slotframe.get_cells_by_mac_addr('test_mac_addr_2') == [cell_2]

    slotframe.delete(cell_2)

    assert slotframe.get_cells_by_mac_addr('test_mac_addr_1') == []
    assert slotframe.get_cells_by_mac_addr('test_mac_addr_2') == []

def test_delete_slotframe(sim_engine):
    sim_engine = sim_engine(diff_config={'exec_numMotes': 1})
    mote = sim_engine.motes[0]
    assert mote.tsch.get_slotframe(0) is not None
    mote.tsch.delete_slotframe(0)
    assert mote.tsch.get_slotframe(0) is None

def test_tx_with_two_slotframes(sim_engine):
    sim_engine = sim_engine(
        diff_config = {
            'app_pkPeriod'            : 0,
            'exec_numMotes'           : 2,
            'exec_numSlotframesPerRun': 1000,
            'secjoin_enabled'         : False,
            'sf_class'                : 'SFNone',
            'conn_class'              : 'Linear',
            'rpl_extensions'          : [],
            'rpl_daoPeriod'           : 0
        }
    )

    # shorthands
    root  = sim_engine.motes[0]
    hop_1 = sim_engine.motes[1]

    # add one slotframe to the two motes
    for mote in sim_engine.motes:
        mote.tsch.add_slotframe(1, 101)

    asn_at_end_of_simulation = (
        sim_engine.settings.tsch_slotframeLength *
        sim_engine.settings.exec_numSlotframesPerRun
    )

    u.run_until_everyone_joined(sim_engine)
    assert sim_engine.getAsn() < asn_at_end_of_simulation

    # put DIO to hop1
    dio = root.rpl._create_DIO()
    dio['mac'] = {'srcMac': root.get_mac_addr()}
    hop_1.rpl.action_receiveDIO(dio)

    # install one TX cells to each slotframe
    for i in range(2):
        hop_1.tsch.addCell(
            slotOffset       = i + 1,
            channelOffset    = 0,
            neighbor         = root.get_mac_addr(),
            cellOptions      = [d.CELLOPTION_TX],
            slotframe_handle = i
        )
        root.tsch.addCell(
            slotOffset       = i + 1,
            channelOffset    = 0,
            neighbor         = hop_1.get_mac_addr(),
            cellOptions      = [d.CELLOPTION_RX],
            slotframe_handle = i
        )

    # the first dedicated cell is scheduled at slot_offset 1, the other is at
    # slot_offset 2
    cell_in_slotframe_0 = hop_1.tsch.get_cells(root.get_mac_addr(), 0)[0]
    cell_in_slotframe_1 = hop_1.tsch.get_cells(root.get_mac_addr(), 1)[0]

    # run until the end of this slotframe
    slot_offset = sim_engine.getAsn() % 101
    u.run_until_asn(sim_engine, sim_engine.getAsn() + (101 - slot_offset - 1))

    # send two application packets, which will be sent over the dedicated cells
    hop_1.app._send_a_single_packet()
    hop_1.app._send_a_single_packet()

    # run for one slotframe
    asn = sim_engine.getAsn()
    assert (asn % 101) == 100 # the next slot is slotoffset 0
    u.run_until_asn(sim_engine, asn + 101)

    # check logs
    ## TX side (hop_1)
    logs = [
        log for log in u.read_log_file(
                filter    = [SimLog.LOG_TSCH_TXDONE['type']],
                after_asn = asn
            ) if log['_mote_id'] == hop_1.id
    ]
    assert len(logs) == 2
    assert (logs[0]['_asn'] % 101) == cell_in_slotframe_0.slot_offset
    assert (logs[1]['_asn'] % 101) == cell_in_slotframe_1.slot_offset

    ## RX side (root)
    logs = [
        log for log in u.read_log_file(
                filter    = [SimLog.LOG_TSCH_RXDONE['type']],
                after_asn = asn
            ) if log['_mote_id'] == root.id
    ]
    assert len(logs) == 2
    assert (logs[0]['_asn'] % 101) == cell_in_slotframe_0.slot_offset
    assert (logs[1]['_asn'] % 101) == cell_in_slotframe_1.slot_offset

    # confirm hop_1 has the minimal cell
    assert len(hop_1.tsch.get_cells(None)) == 1
    assert (
        hop_1.tsch.get_cells(None)[0].options == [
            d.CELLOPTION_TX,
            d.CELLOPTION_RX,
            d.CELLOPTION_SHARED
        ]
    )

@pytest.fixture(params=[0, 1, 10, 101])
def fixture_num_cells(request):
    return request.param
def test_print_slotframe(sim_engine, fixture_num_cells):
    sim_engine = sim_engine() # need for log

    slotframe = SlotFrame(None, 1, 101)
    # install cells
    for i in range(fixture_num_cells):
        slot_offset = i
        channel_offset = random.randint(0, 65535)
        slotframe.add(Cell(slot_offset, channel_offset, []))

    print(slotframe)
    str_slotframe = str(slotframe)
    assert 'length: 101' in str_slotframe
    assert 'num_cells: {0}'.format(fixture_num_cells) in str_slotframe

CELL_TX = [d.CELLOPTION_TX]
CELL_RX = [d.CELLOPTION_RX]
CELL_TX_SHARED = [d.CELLOPTION_TX, d.CELLOPTION_SHARED]
CELL_TX_RX_SHARED = [d.CELLOPTION_TX, d.CELLOPTION_RX, d.CELLOPTION_SHARED]
@pytest.fixture(params=[CELL_TX, CELL_RX, CELL_TX_SHARED, CELL_TX_RX_SHARED])
def fixture_cell_options(request):
    return request.param

@pytest.fixture(params=[None, True])
def fixture_mac_addr(request):
    return request.param

def test_print_cell(sim_engine, fixture_cell_options, fixture_mac_addr):

    sim_engine = sim_engine()
    if fixture_mac_addr is True:
        mac_addr = sim_engine.motes[0].get_mac_addr()
    else:
        mac_addr = fixture_mac_addr

    slot_offset = random.randint(0, 65535)
    channel_offset = random.randint(0, 65535)

    cell = Cell(slot_offset, channel_offset, fixture_cell_options, mac_addr)

    print(cell)
    str_cell = str(cell)
    assert 'slot_offset: {0}'.format(slot_offset) in str_cell
    assert 'channel_offset: {0}'.format(channel_offset) in str_cell
    assert 'mac_addr: {0}'.format(mac_addr) in str_cell
    assert 'options: [{0}]'.format(', '.join(fixture_cell_options)) in str_cell

def test_slotframe_get_cells_filtered(sim_engine):
    """
    Unit test for Slotframe class method slotframe_get_cells_filtered
    Test if we can get the cells filtered by options, MAC address or both
    """
    sim_engine = sim_engine() # need for log

    neighbor_mac_addr_1 = 'test_mac_addr_1'
    neighbor_mac_addr_2 = 'test_mac_addr_2'
    neighbor_mac_addr_3 = None
    slotframe = SlotFrame(None, 1, 101)

    # create cells
    cell_tx_1 = Cell(0, 0, [d.CELLOPTION_TX], neighbor_mac_addr_1)
    cell_rx_1 = Cell(1, 0, [d.CELLOPTION_RX], neighbor_mac_addr_2)
    cell_rx_2 = Cell(1, 0, [d.CELLOPTION_RX], neighbor_mac_addr_3)
    cells = [cell_tx_1, cell_rx_1, cell_rx_2]

    # add cells to slotframe
    for c in cells:
        slotframe.add(c)

    # check if all cells are returned ()
    assert slotframe.get_cells_filtered() == cells

    # check if only tx cells are returned
    assert slotframe.get_cells_filtered(cell_options=[d.CELLOPTION_TX]) == [cell_tx_1]

    # check if only rx cells are returned
    assert slotframe.get_cells_filtered(cell_options=[d.CELLOPTION_RX]) == [cell_rx_1, cell_rx_2]

    # check if only cells that match mac_address are returned
    assert slotframe.get_cells_filtered(mac_addr=neighbor_mac_addr_1) == \
           [c for c in cells if c.mac_addr == neighbor_mac_addr_1]

    # check if only cells that match None mac_address are returned
    assert slotframe.get_cells_filtered(mac_addr=None) == \
           [c for c in cells if c.mac_addr is None]

def test_slotframe_get_available_slots(sim_engine):
    """
    Unit test for Slotframe class method get_available_slots
    Test if we can get the list of offsets for slots that are not in use
    """
    sim_engine = sim_engine() # need for log

    neighbor_mac_addr_1 = 'test_mac_addr_1'
    neighbor_mac_addr_2 = 'test_mac_addr_2'
    slotframe = SlotFrame(None, 1, 101)

    # create cells
    cell_tx_1 = Cell(0, 0, [d.CELLOPTION_TX], neighbor_mac_addr_1)
    cell_rx_1 = Cell(1, 0, [d.CELLOPTION_RX], neighbor_mac_addr_2)
    cells = [cell_tx_1, cell_rx_1]

    # add cells to slotframe
    for c in cells:
        slotframe.add(c)

    # check if all slot offsets are returned except the one reserved
    assert slotframe.get_available_slots() == [i for i in range(2, 101)]

def test_slotframe_set_length_without_cells(sim_engine):
    """
    Test if we can change the slotframe length when no cells are allocated
    """
    sim_engine = sim_engine() # need for log

    slotframe = SlotFrame(None, 1, 101)

    # decrease the slotframe length
    new_length = 50
    slotframe.set_length(new_length)
    assert slotframe.length == new_length

    # increase the slotframe length
    new_length = 150
    slotframe.set_length(new_length)
    assert slotframe.length == new_length

def test_slotframe_set_length_with_cells(sim_engine):
    """
    Test if we can change the slotframe length when cells are allocated
    """
    sim_engine = sim_engine() # need for log

    neighbor_mac_addr_1 = 'test_mac_addr_1'
    neighbor_mac_addr_2 = 'test_mac_addr_2'
    slotframe = SlotFrame(None, 1, 101)

    # create cells
    cell_0  = Cell(0,  0, [d.CELLOPTION_TX], neighbor_mac_addr_1)
    cell_70 = Cell(70, 0, [d.CELLOPTION_TX], neighbor_mac_addr_2)
    cells = [cell_0, cell_70]

    # add cells to slotframe
    for c in cells:
        slotframe.add(c)

    # decrease the slotframe length
    assert len(slotframe.get_busy_slots()) == len(cells)
    new_length = 50
    slotframe.set_length(new_length)
    assert slotframe.length == new_length
    assert len(slotframe.get_busy_slots()) == len(cells) - 1  # make sure cell is delete

    # make sure we cannot add a cell after new length
    with pytest.raises(Exception):
        slotframe.add(cell_70)

    # increase the slotframe length
    new_length = 150
    slotframe.set_length(new_length)
    assert slotframe.length == new_length
    assert len(slotframe.get_busy_slots()) == len(cells) - 1  # make sure we have the right amount of cells
