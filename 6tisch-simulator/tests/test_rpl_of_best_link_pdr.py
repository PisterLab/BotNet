import copy

import SimEngine.Mote.MoteDefines as d
import tests.test_utils as u
from SimEngine.Mote.rpl import RplOFBestLinkPDR

def test_free_run(sim_engine):
    sim_engine = sim_engine(
        diff_config = {'rpl_of': 'OFBestLinkPDR'}
    )
    u.run_until_end(sim_engine)


def test_parent_selection(sim_engine):
    sim_engine = sim_engine(
        diff_config = {
            'exec_numMotes'  : 4,
            'conn_class'     : 'FullyMeshed',
            'phy_numChans'   : 1,
            'rpl_of'         : 'OFBestLinkPDR',
            'secjoin_enabled': False
        }
    )

    # shorthands
    connectivity_matrix = sim_engine.connectivity.matrix
    mote_0 = sim_engine.motes[0]
    mote_1 = sim_engine.motes[1]
    mote_2 = sim_engine.motes[2]
    mote_3 = sim_engine.motes[3]
    channel = d.TSCH_HOPPING_SEQUENCE[0]

    # disable the link between mote 0 and mote 3
    connectivity_matrix.set_pdr_both_directions(
        mote_0.id, mote_3.id, channel, 0.0
    )

    # degrade link PDRs to ACCEPTABLE_LOWEST_PDR
    # - between mote 0 and mote 2
    # - between mote 3 and mote 1
    connectivity_matrix.set_pdr_both_directions(
        mote_0.id,
        mote_2.id,
        channel,
        RplOFBestLinkPDR.ACCEPTABLE_LOWEST_PDR
    )
    connectivity_matrix.set_pdr_both_directions(
        mote_1.id,
        mote_3.id,
        channel,
        RplOFBestLinkPDR.ACCEPTABLE_LOWEST_PDR
    )

    # now we have links shown below, () denotes link PDR:
    #
    #         [mote_0]
    #        /        \
    #     (1.0)      (0.3)
    #      /            \
    # [mote_1]--(1.0)--[mote_2]
    #      \            /
    #     (0.3)      (1.0)
    #        \        /
    #         [mote_3]

    # get all the motes synchronized
    eb = mote_0.tsch._create_EB()
    eb_dummy = {
        'type':            d.PKT_TYPE_EB,
        'mac': {
            'srcMac':      '00-00-00-AA-AA-AA',     # dummy
            'dstMac':      d.BROADCAST_ADDRESS,     # broadcast
            'join_metric': 1000
        }
    }
    mote_1.tsch._action_receiveEB(eb)
    mote_1.tsch._action_receiveEB(eb_dummy)
    mote_2.tsch._action_receiveEB(eb)
    mote_2.tsch._action_receiveEB(eb_dummy)
    mote_3.tsch._action_receiveEB(eb)
    mote_3.tsch._action_receiveEB(eb_dummy)

    # make sure all the motes don't have their parents
    for mote in sim_engine.motes:
        assert mote.rpl.getPreferredParent() is None

    # test starts
    # step 1: make mote_1 and mote_2 connect to mote_0
    dio = u.create_dio(mote_0)
    mote_1.sixlowpan.recvPacket(dio)
    mote_2.sixlowpan.recvPacket(dio)
    assert mote_1.rpl.of.preferred_parent['mote_id'] == mote_0.id
    assert mote_2.rpl.of.preferred_parent['mote_id'] == mote_0.id

    # step 2: give a DIO of mote_1 to mote_2; then mote_2 should
    # switch its parent to mote_0
    dio = u.create_dio(mote_1)
    mote_2.sixlowpan.recvPacket(dio)
    assert mote_2.rpl.of.preferred_parent['mote_id'] == mote_1.id

    # step 3: give a DIO of mote_2 to mote_1; mote_1 should stay at
    # mote_0
    dio = u.create_dio(mote_2)
    mote_1.sixlowpan.recvPacket(dio)
    assert mote_1.rpl.of.preferred_parent['mote_id'] == mote_0.id

    # step 4: give a DIO of mote_1 to mote_3; mote_3 should connect to
    # mote_1
    dio = u.create_dio(mote_1)
    mote_3.sixlowpan.recvPacket(dio)
    assert mote_3.rpl.of.preferred_parent['mote_id'] == mote_1.id

    # step 5: give a DIO of mote_2 to mote_3; mote_3 should switch to
    # mote_2
    dio = u.create_dio(mote_2)
    mote_3.sixlowpan.recvPacket(dio)
    assert mote_3.rpl.of.preferred_parent['mote_id'] == mote_2.id

    # step 6: give a DIO of mote_0 to mote_3; mote_3 should stay at
    # mote_2
    dio = u.create_dio(mote_0)
    mote_3.sixlowpan.recvPacket(dio)
    assert dio['app']['rank'] < u.create_dio(mote_2)['app']['rank']
    assert mote_3.rpl.of.preferred_parent['mote_id'] == mote_2.id

    # step 7: give a fake DIO to mote_2 which has a very low rank and
    # mote_3's MAC address as its source address. mote_2 should ignore
    # this DIO to prevent a routing loop and stay at mote_1
    dio = u.create_dio(mote_3)
    dio['app']['rank'] = 0
    mote_2.sixlowpan.recvPacket(dio)
    assert mote_2.rpl.of.preferred_parent['mote_id'] == mote_1.id

def test_etx_limit(sim_engine):
    sim_engine = sim_engine(
        diff_config = {
            'exec_numMotes'  : 2,
            'conn_class'     : 'FullyMeshed',
            'phy_numChans'   : 1,
            'rpl_of'         : 'OFBestLinkPDR',
            'secjoin_enabled': False
        }
    )

    # shorthands
    connectivity_matrix = sim_engine.connectivity.matrix
    mote_0 = sim_engine.motes[0]
    mote_1 = sim_engine.motes[1]
    mote_0_mac_addr = mote_0.get_mac_addr()
    ch = d.TSCH_HOPPING_SEQUENCE[0]

    u.get_join(mote_0, mote_1)

    # now the preferred parent of mote_1 is mote_0
    assert mote_1.rpl.of.preferred_parent['mote_id'] == mote_0.id

    # lower PDR value between mote_0 and mote_1 below the acceptable
    # lowest PDR
    connectivity_matrix.set_pdr_both_directions(
        mote_0.id,
        mote_1.id,
        ch,
        (RplOFBestLinkPDR.ACCEPTABLE_LOWEST_PDR * 0.99)
    )
    mote_1.rpl.of.update_etx(None, mote_0_mac_addr, False)
    # mote_1 should lose its preferred parent
    assert mote_1.rpl.of.preferred_parent['mac_addr'] is None

    # if the link gets better, mote_0 is selected as the preferred
    # parent again
    connectivity_matrix.set_pdr_both_directions(mote_0.id, mote_1.id, ch, 1.0)
    mote_1.rpl.of.update_etx(None, mote_0_mac_addr, False)
    assert mote_1.rpl.of.preferred_parent['mote_id'] == mote_0.id

def test_rejoin(sim_engine):
    sim_engine = sim_engine(
        diff_config = {
            'exec_numMotes'  : 4,
            'conn_class'     : 'FullyMeshed',
            'phy_numChans'   : 1,
            'rpl_of'         : 'OFBestLinkPDR',
            'secjoin_enabled': False
        }
    )
    root = sim_engine.motes[0]
    mote_1 = sim_engine.motes[1]
    mote_2 = sim_engine.motes[2]
    mote_3 = sim_engine.motes[3]

    parent = root
    # make a linear topology
    for child in [mote_1, mote_2, mote_3]:
        u.get_join(parent, child)
        assert child.rpl.getPreferredParent() == parent.get_mac_addr()
        parent = child

    # trigger the local repair at mote_1
    mote_1.rpl.local_repair()
    assert mote_1.rpl.getPreferredParent() is None

    # update mote_3's parent, which should be None since mote_1,
    # mote_2's parent, is detached from the dodag
    mote_3.rpl.of.update_etx(None, None, None)
    assert mote_3.rpl.getPreferredParent() is None

    # put mote_1 back to the dodag
    mote_1.rpl.action_receiveDIO(u.create_dio(root))
    assert mote_1.rpl.getPreferredParent() == root.get_mac_addr()

    # update mote_3 again; its parent should be back, too
    mote_3.rpl.of.update_etx(None, None, None)
    assert mote_3.rpl.getPreferredParent() == mote_2.get_mac_addr()
    # mote_3 should have DODAG ID, its trickle timer should be
    # started, ...
    assert mote_3.rpl.dodagId
    assert mote_3.rpl.trickle_timer.is_running
    assert not mote_3.rpl.dis_timer_is_running
