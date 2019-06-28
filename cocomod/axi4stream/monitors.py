#!/usr/bin/env python
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

from collections import namedtuple

from cocotb.decorators import coroutine
from cocotb.monitors import BusMonitor
from cocotb.triggers import First, ReadOnly, RisingEdge


class Axi4Stream(BusMonitor):
    """AXI4Stream bus monitor"""

    _signals = ["TVALID"]

    _optional_signals = [
        "TREADY", "TDATA", "TLAST", "TSTRB", "TKEEP", "TID", "TDEST", "TUSER"
    ]

    _optional_data_signals = \
        tuple(signal for signal in _optional_signals if signal != "TREADY")

    Axi4StreamTransfer = namedtuple('Axi4StreamTransfer',
                                    _optional_data_signals)

    def __init__(self, *args, packets=False, aux_signals=False, **kwargs):
        """Initialization of Axi4Stream

        Args:
            *args: passed directly to the BusMonitor parent constructor.
            packets (bool, optional): wait for a high TLAST to call _recv.
                Defaults to False (call _recv on every transaction).
            aux_signals (bool, optional): return an Axi4StreamTransfer named
                tuple containing all the data signals, instead of just TDATA.
                Defaults to False.
            **kwargs: passed directly to the BusMonitor parent constructor.
        """
        BusMonitor.__init__(self, *args, **kwargs)

        if packets and not hasattr(self.bus, "TLAST"):
            raise AttributeError("\'packets=True\', but \'TLAST\' is missing "
                                 "on this bus")

        self.packets = packets
        self.aux_signals = aux_signals

        self.bus_optional_signals = \
            tuple(signal for signal in Axi4Stream._optional_data_signals
                  if hasattr(self.bus, signal))

    @coroutine
    def _monitor_recv(self):
        """Watch the pins and reconstruct transfers and packets."""

        def valid_transfer():
            if hasattr(self.bus, "TREADY"):
                return self.bus.TVALID.value and self.bus.TREADY.value
            return self.bus.TVALID.value

        # Avoid spurious object creation by recycling
        clk_redge = RisingEdge(self.clock)
        rdonly = ReadOnly()

        if hasattr(self.bus, "TREADY"):
            handshake_signals_redge = First(RisingEdge(self.bus.TVALID),
                                            RisingEdge(self.bus.TREADY))
        else:
            handshake_signals_redge = RisingEdge(self.bus.TVALID)

        packet = []

        yield clk_redge
        yield rdonly

        while True:

            while valid_transfer():
                if self.aux_signals:
                    packet.append(Axi4Stream.Axi4StreamTransfer._make(
                        (getattr(self.bus, signal).value.buff
                         if signal in self.bus_optional_signals else None
                         for signal in Axi4Stream._optional_data_signals)))
                else:
                    packet.append(self.bus.TDATA.value.buff if
                                  hasattr(self.bus, "TDATA") else None)

                if not self.packets or \
                   not hasattr(self.bus, "TLAST") or \
                   hasattr(self.bus, "TLAST") and self.bus.TLAST.value:
                    self._recv(packet)
                    packet = []

                yield clk_redge
                yield rdonly

            yield handshake_signals_redge
