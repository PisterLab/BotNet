import pytest

from SimEngine.SimEngine import SimEngine
from SimEngine.SimSettings import SimSettings
from SimEngine.SimLog import SimLog
from SimEngine.Connectivity import Connectivity

# =========================== fixtures ========================================

@pytest.fixture(params=[SimSettings, SimEngine, Connectivity, SimLog])
def singleton_class(request):
    return request.param

# =========================== tests ===========================================

def test_instantiate(sim_engine, singleton_class):
    sim_engine = sim_engine()
    instance_1 = singleton_class()
    instance_2 = singleton_class()
    assert id(instance_1) == id(instance_2)


def test_destroy(sim_engine, singleton_class):
    sim_engine = sim_engine()
    if singleton_class == Connectivity:
        instance_1 = singleton_class(sim_engine)
    else:
        instance_1 = singleton_class()
    instance_1_id = id(instance_1)
    instance_1.destroy()
    if singleton_class == Connectivity:
        instance_2 = singleton_class(sim_engine)
    else:
        instance_2 = singleton_class()
    assert instance_1_id != id(instance_2)
