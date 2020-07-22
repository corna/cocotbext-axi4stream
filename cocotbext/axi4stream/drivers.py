#!/usr/bin/env python3
# Copyright (c) 2019 Nicola Corna <nicola.corna@polimi.it>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of Potential Ventures Ltd,
#       SolarFlare Communications Inc nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Drivers for Advanced Microcontroller Bus Architecture."""

import cocotb
from cocotb.drivers import BusDriver
from cocotb.triggers import ClockCycles, FallingEdge, First, RisingEdge
from cocotb.result import TestFailure

import copy


class Axi4StreamMaster(BusDriver):
    """
    AXI4-Stream Master
    """

    _signals = ["TVALID"]

    _optional_signals = [
        "TREADY", "TDATA", "TLAST", "TSTRB", "TKEEP", "TID", "TDEST", "TUSER"
    ]

    def __init__(self, entity, name, clock):
        """
            Initialization of AxiStreamMaster

            Args:
                entity: handle to the simulator entity
                name: Name of the bus
                clock: handle to the clk associated with this bus
        """

        BusDriver.__init__(self, entity, name, clock)
        self.clock = clock

        # Drive some sensible defaults (setimmediatevalue to avoid x asserts)
        self.bus.TVALID.setimmediatevalue(0)
        for signal in self._optional_signals:
            try:
                default_value = \
                    "1" * signal.n_bits if signal in ("TSTRB", "TKEEP") else 0
                getattr(self.bus, signal).setimmediatevalue(default_value)
            except AttributeError:
                pass

    @cocotb.coroutine
    async def write(self, data, sync=True, tlast_on_last=True):
        """
        Write one or more values on the bus.

        Args:
            data (int/dict or iterable of int/dict): the data values to write.
                Each dict represents an AXI4-Stream transaction, where the
                dict's keys are the signal names and the values are the values
                to write. Missing signals are kept constant.
                Each int represents the TDATA signal in the AXI4-Stream
                transaction (so, they are equivalent to {"TDATA": int_value}).
            sync (bool, optional): wait for rising edge on clock initially.
                Defaults to True.
            tlast_on_last(bool, optional): assert TLAST on the last word
                written on the bus.
                Defaults to True.
        """

        try:
            if isinstance(data, dict):
                # Treat dict as not iterable to avoid wrong results when using
                # enumerate method to retrieve data signals.
                raise TypeError
            iter(data)
        except TypeError:
            data = (data,)    # If data is not iterable, make it

        data = copy.copy(data)

        if sync:
            await RisingEdge(self.clock)

        self.bus.TVALID <= 1

        for index, word in enumerate(data):
            # If word is not a dict, make it (using word as "TDATA")
            if not isinstance(word, dict):
                word = {"TDATA": word}

            for signal, value in word.items():
                err_msg = \
                    f"During transfer {index}, signal {signal} has been "
                "passed, but it is "
                if signal == 'TREADY':
                    raise TestFailure(err_msg + "an input for the driver")
                elif signal == 'TLAST' and tlast_on_last:
                    raise TestFailure(err_msg + "already controlled by the "
                                                "driver (tlast_on_last=True)")
                elif signal not in Axi4StreamMaster._optional_signals:
                    raise TestFailure(err_msg + "not a valid "
                                                "AXI4-Stream signal")

                try:
                    getattr(self.bus, signal) <= value
                except AttributeError:
                    raise TestFailure(err_msg + "not present on the bus")

            if hasattr(self.bus, "TLAST") and tlast_on_last and \
               index == len(data) - 1:
                self.bus.TLAST <= 1

            await RisingEdge(self.clock)

            while True:
                if not hasattr(self.bus, "TREADY") or self.bus.TREADY.value:
                    break
                await RisingEdge(self.clock)

        if hasattr(self.bus, "TLAST") and tlast_on_last:
            self.bus.TLAST <= 0

        self.bus.TVALID <= 0

    @property
    def n_bits(self):
        return self.bus.TDATA.value.n_bits


class Axi4StreamSlave(BusDriver):
    """
    AXI4-Stream Slave

    Generates configurable TREADY patterns.
    """

    _signals = ["TVALID"]

    # Only TREADY is used in this design, all other signals are unused
    _optional_signals = [
        "TREADY", "TDATA", "TLAST", "TSTRB", "TKEEP", "TID", "TDEST", "TUSER"
    ]

    def __init__(self, entity, name, clock, tready_delay=-1,
                 consecutive_transfers=0):
        """
            Initialization of AxiStreamSlave

            Args:
                entity: handle to the simulator entity
                name: name of the bus
                clock: handle to the clk associated with this bus
                tready_delay (int or callable, optional): number of delay clock
                    cycles between a high TVALID and the assertion of TREADY.
                    Can also be a function, which is called at the TVALID
                    rising edge should return the number of delay cycles to
                    assert TREADY.
                    Defaults to -1 , which sets TREADY always to 1, regardless
                    of the value of TVALID.
                consecutive_transfers (int or callable, optional): the maximum
                    number of uninterrupted transfers (high TVALID and TREADY
                    on consecutive clock cycles) after which TREADY will be
                    de-asserted and the tready_delay will be restarted.
                    Can also be a function, which is called at the beginning of
                    each transfer and should return the maximum allowed number
                    of consecutive transfers.
                    Default to 0, which allows an unlimited number of
                    consecutive transfers.
        """

        BusDriver.__init__(self, entity, name, clock)

        # If TREADY is not present, this Driver does nothing
        if hasattr(self.bus, "TREADY"):
            if not callable(tready_delay) and tready_delay == -1:
                # If TREADY has to be always high, just set it to 1
                self.bus.TREADY.setimmediatevalue(1)
            else:
                # If not, set it to zero and fork _receive_data
                self.bus.TREADY.setimmediatevalue(0)
                self.clock = clock
                self.tready_delay = tready_delay
                self.consecutive_transfers = consecutive_transfers

                cocotb.fork(self._receive_data())

    @cocotb.coroutine
    async def _receive_data(self):

        while True:
            # Wait for a high TVALID, if not already high
            if not self.bus.TVALID.value:
                await RisingEdge(self.bus.TVALID)

            # Wait either for the required number of clock cycles or for a low
            # TVALID. By AXI4-Stream standard, the master should not de-assert
            # TVALID until at least one transfer has been performed but, if it
            # does it anyways, just re-start the wait.
            if callable(self.tready_delay):
                tready_high_delay = ClockCycles(self.clock,
                                                self.tready_delay(self.bus))
            else:
                tready_high_delay = ClockCycles(self.clock, self.tready_delay)

            trigger = await First(tready_high_delay,
                                  FallingEdge(self.bus.TVALID))

            if trigger is tready_high_delay:
                self.bus.TREADY <= 1

                if callable(self.consecutive_transfers):
                    num_cycles = self.consecutive_transfers(self.bus)
                else:
                    num_cycles = self.consecutive_transfers

                if num_cycles != 0:
                    await First(ClockCycles(self.clock, num_cycles),
                                FallingEdge(self.bus.TVALID))
                else:
                    await FallingEdge(self.bus.TVALID)

                self.bus.TREADY <= 0
