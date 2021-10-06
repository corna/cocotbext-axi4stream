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

"""Monitors for Advanced Microcontroller Bus Architecture."""

import cocotb
from cocotb_bus.monitors import BusMonitor
from cocotb.triggers import RisingEdge


class Axi4Stream(BusMonitor):
    """AXI4Stream bus monitor"""

    _signals = ["TVALID"]

    _optional_signals = [
        "TREADY", "TDATA", "TLAST", "TSTRB", "TKEEP", "TID", "TDEST", "TUSER"
    ]

    _optional_data_signals = \
        tuple(signal for signal in _optional_signals if signal != "TREADY")

    def __init__(self, *args, packets=False, aux_signals=False,
                 data_type="buff", **kwargs):
        """Initialization of Axi4Stream

        Args:
            *args: passed directly to the BusMonitor parent constructor.
            packets (bool, optional): wait for a high TLAST to call _recv.
                Defaults to False (call _recv on every transfer).
            aux_signals (bool, optional): when true, return a dict for each
                AXI4-Stream transfer where the key is the name of the signal
                and the value is the value of it.
                When false, return an int for each transfer representing the
                value of the TDATA signal
            data_type (str, optional): select the data type passed to _recv,
                either "buff" (for binary buffers of bytes) or "integer".
            **kwargs: passed directly to the BusMonitor parent constructor.
        """

        BusMonitor.__init__(self, *args, **kwargs)

        if packets and not hasattr(self.bus, "TLAST"):
            raise AttributeError("\'packets=True\', but \'TLAST\' is missing "
                                 "on this bus")

        if data_type not in ("buff", "integer"):
            raise AttributeError("data_type must be either \"buff\" or "
                                 "\"integer\"")

        self.packets = packets
        self.aux_signals = aux_signals
        self.data_type = data_type

        self.bus_optional_signals = \
            tuple(signal for signal in Axi4Stream._optional_data_signals
                  if hasattr(self.bus, signal) and
                  (signal != "TLAST" or not packets))

    @cocotb.coroutine
    async def _monitor_recv(self):
        """Watch the pins and reconstruct transfers and packets."""

        def valid_transfer():
            if hasattr(self.bus, "TREADY"):
                return self.bus.TVALID.value and self.bus.TREADY.value
            return self.bus.TVALID.value

        def get_signal_value(signal):
            handle = getattr(self.bus, signal, None)
            return getattr(handle.value, self.data_type) if handle else None

        # Avoid spurious object creation by recycling
        clk_redge = RisingEdge(self.clock)

        packet = []
        while True:
            await clk_redge

            if valid_transfer():
                if self.aux_signals:
                    packet.append({signal: get_signal_value(signal)
                                  for signal in self.bus_optional_signals})
                else:
                    packet.append(get_signal_value("TDATA"))

                if not self.packets:
                    self._recv(packet[0])
                    packet = []
                elif self.bus.TLAST.value:
                    self._recv(packet)
                    packet = []
