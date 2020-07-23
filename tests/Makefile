PWD				:= $(shell pwd)

SIM				?= ghdl
SIM_ARGS		?= --wave=$(PWD)/build/waveform.ghw

TOPLEVEL_LANG	= vhdl

SIM_BUILD		= $(PWD)/build
MODULE			= axi4stream_inverter
TOPLEVEL		= axi4stream_inverter

VHDL_SOURCES	= $(PWD)/axi4stream_inverter.vhd

include $(shell cocotb-config --makefiles)/Makefile.inc
include $(shell cocotb-config --makefiles)/Makefile.sim
