library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity axi4stream_inverter is
	generic (
		C_S_AXIS_TDATA_WIDTH	: natural := 32;
		C_S_AXIS_TUSER_WIDTH	: natural := 16;
		C_S_AXIS_TDEST_WIDTH	: natural := 8;
		C_S_AXIS_TID_WIDTH		: natural := 8
	);
	port (
		aclk			: in std_logic;
		aresetn			: in std_logic;

		s_axis_tvalid	: in std_logic;
		s_axis_tdata	: in std_logic_vector(C_S_AXIS_TDATA_WIDTH-1 downto 0);
		s_axis_tstrb	: in std_logic_vector(C_S_AXIS_TDATA_WIDTH/8-1 downto 0);
		s_axis_tkeep	: in std_logic_vector(C_S_AXIS_TDATA_WIDTH/8-1 downto 0);
		s_axis_tdest	: in std_logic_vector(C_S_AXIS_TDEST_WIDTH-1 downto 0);
		s_axis_tid		: in std_logic_vector(C_S_AXIS_TID_WIDTH-1 downto 0);
		s_axis_tuser	: in std_logic_vector(C_S_AXIS_TUSER_WIDTH-1 downto 0);
		s_axis_tlast	: in std_logic;
		s_axis_tready	: out std_logic;

		m_axis_tvalid	: out std_logic;
		m_axis_tdata	: out std_logic_vector(C_S_AXIS_TDATA_WIDTH-1 downto 0);
		m_axis_tstrb	: out std_logic_vector(C_S_AXIS_TDATA_WIDTH/8-1 downto 0);
		m_axis_tkeep	: out std_logic_vector(C_S_AXIS_TDATA_WIDTH/8-1 downto 0);
		m_axis_tdest	: out std_logic_vector(C_S_AXIS_TDEST_WIDTH-1 downto 0);
		m_axis_tid		: out std_logic_vector(C_S_AXIS_TID_WIDTH-1 downto 0);
		m_axis_tuser	: out std_logic_vector(C_S_AXIS_TUSER_WIDTH-1 downto 0);
		m_axis_tlast	: out std_logic;
		m_axis_tready	: in std_logic
	);
end axi4stream_inverter;

architecture Behavioral of axi4stream_inverter is

	signal m_axis_tvalid_int	: std_logic;
	signal s_axis_tready_int	: std_logic;

begin

	-- We can accept new data from the slave interface if the reset is not
	-- active and:
	--  * either our memory element is empty (not m_axis_tvalid_int), or
	--  * we can write on the master interface
	s_axis_tready_int	<= aresetn and (m_axis_tready or not m_axis_tvalid_int);

	m_axis_tvalid		<= m_axis_tvalid_int;
	s_axis_tready		<= s_axis_tready_int;

	process(aclk)
	begin
		if rising_edge(aclk) then

			if aresetn = '0' then

				m_axis_tvalid_int	<= '0';

			else

				-- If slave valid is 1, raise master valid.
				-- If it is low, keep the previous value until a high ready,
				-- then reset to 0.
				if s_axis_tvalid = '1' then
					m_axis_tvalid_int	<= '1';
				elsif m_axis_tready = '1' then
					m_axis_tvalid_int	<= '0';
				end if;

				-- If the transaction in this clock cycle has been performed (on
				-- the slave port), then update the data on the master port.
				if s_axis_tvalid = '1' and s_axis_tready_int = '1' then
					m_axis_tdata	<= not s_axis_tdata;
					m_axis_tstrb	<= s_axis_tstrb;
					m_axis_tkeep	<= s_axis_tkeep;
					m_axis_tdest	<= s_axis_tdest;
					m_axis_tid		<= s_axis_tid;
					m_axis_tuser	<= not s_axis_tuser;
					m_axis_tlast	<= s_axis_tlast;
				end if;

			end if;

		end if;
	end process;

end Behavioral;
