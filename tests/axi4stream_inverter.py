#!//usr//bin//env python3

from random import randint

import cocotb
from cocotb.clock import Clock
from cocotb.regression import TestFactory
from cocotb.scoreboard import Scoreboard
from cocotb.triggers import RisingEdge, Timer
from cocotbext.axi4stream.drivers import Axi4StreamMaster, Axi4StreamSlave
from cocotbext.axi4stream.monitors import Axi4Stream

CLK_PERIOD = 10


@cocotb.coroutine
async def setup_dut(dut):
    cocotb.start_soon(Clock(dut.aclk, CLK_PERIOD, "ns").start())
    dut.aresetn.value = 0
    await Timer(CLK_PERIOD * 2, "ns")
    dut.aresetn.value = 1
    await Timer(CLK_PERIOD * 2, "ns")


@cocotb.test()
async def test_tdata(dut, packets_num=5, packet_size=(10, 100), delay=-1, consecutive_transfers=0):
    """Test TDATA"""

    tdata_width = dut.C_S_AXIS_TDATA_WIDTH.value.integer

    axis_m = Axi4StreamMaster(dut, "s_axis", dut.aclk)
    axis_s = Axi4StreamSlave(dut, "m_axis", dut.aclk, delay, consecutive_transfers)
    axis_monitor = Axi4Stream(dut, "m_axis", dut.aclk, data_type="integer", packets=True)

    await setup_dut(dut)

    input = []
    output = []

    # Build the input and output packets
    for i in range(packets_num):
        input.append([randint(0, 2**tdata_width - 1) for i in range(randint(*packet_size))])
        output.append([word ^ 2**tdata_width - 1 for word in input[-1]])

    scoreboard = Scoreboard(dut)
    scoreboard.add_interface(axis_monitor, output)

    # Write the input packets
    for packet in input:
        await axis_m.write(packet)

    # Wait until output is empty (so, all the packets have been received)
    while output:
        await RisingEdge(dut.aclk)

    await RisingEdge(dut.aclk)


@cocotb.test()
async def test_aux(dut, packets_num=5, packet_size=(10, 100), delay=-1, consecutive_transfers=0):
    """Test all the auxiliary AXI4-Stream signals"""

    tdata_width = dut.C_S_AXIS_TDATA_WIDTH.value.integer
    tdest_width = dut.C_S_AXIS_TDEST_WIDTH.value.integer
    tid_width = dut.C_S_AXIS_TID_WIDTH.value.integer
    tuser_width = dut.C_S_AXIS_TUSER_WIDTH.value.integer

    axis_m = Axi4StreamMaster(dut, "s_axis", dut.aclk)
    axis_s = Axi4StreamSlave(dut, "m_axis", dut.aclk, delay, consecutive_transfers)
    axis_monitor = Axi4Stream(dut, "m_axis", dut.aclk, data_type="integer", packets=True, aux_signals=True)

    await setup_dut(dut)

    input = []
    output = []

    # Build the input and output packets
    for i in range(packets_num):
        first_word = {
            "TDATA": randint(0, 2**tdata_width - 1),
            "TSTRB": randint(0, 2**(tdata_width // 8) - 1),
            "TKEEP": 2**(tdata_width // 8) - 1,
            "TDEST": randint(0, 2**tdest_width - 1),
            "TID": randint(0, 2**tid_width - 1),
            "TUSER": randint(0, 2**tuser_width - 1),
        }
        second_word = {
            "TDATA": randint(0, 2**tdata_width - 1),
            "TSTRB": 2**(tdata_width // 8) - 1
        }
        input.append(
            [first_word, second_word] +
            [randint(0, 2**tdata_width - 1) for i in range(randint(*packet_size))])

        output.append([])
        for input_word in input[-1]:
            output[-1].append({})
            for signal in ("TDATA", "TSTRB", "TKEEP", "TDEST", "TID", "TUSER"):
                if signal == "TDATA" and isinstance(input_word, int):
                    output[-1][-1]["TDATA"] = input_word
                else:
                    try:
                        # If input_word has that signal, copy it, ...
                        output[-1][-1][signal] = input_word[signal]
                    except (KeyError, TypeError):
                        # ...if not, use the last value
                        output[-1][-1][signal] = output[-1][-2][signal]

        for output_word in output[-1]:
            # Flip TDATA and TUSER
            output_word["TDATA"] ^= 2**tdata_width - 1
            output_word["TUSER"] ^= 2**tuser_width - 1

    scoreboard = Scoreboard(dut)
    scoreboard.add_interface(axis_monitor, output)

    # Write the input packets
    for packet in input:
        await axis_m.write(packet)

    # Wait until output_tdata is empty (so, all the packets have been received)
    while output:
        await RisingEdge(dut.aclk)


tdata_test_factory = TestFactory(test_tdata)
tdata_test_factory.add_option('delay', (0, 1, lambda dut: randint(2, 10)))
tdata_test_factory.add_option('consecutive_transfers',
                              (0, 1, 5, lambda dut: randint(1, 5)))
tdata_test_factory.generate_tests()

aux_test_factory = TestFactory(test_aux)
aux_test_factory.add_option('delay', (0, 1, lambda dut: randint(2, 10)))
aux_test_factory.add_option('consecutive_transfers',
                            (0, 1, 5, lambda dut: randint(1, 5)))
aux_test_factory.generate_tests()
