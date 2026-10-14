# ==============================================================================
# Tiny Tapeout Cocotb Test Suite for tt_um_shlomo_fifo
# Single Self-Contained Verification Suite for Dual-Clock Asynchronous FIFO
# ==============================================================================

import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge


# ==============================================================================
# ASYNC FIFO TESTBENCH HELPER (BFM & DRIVER)
# ==============================================================================
class AsyncFIFOTester:
    """
    Bus Functional Model & Driver for Tiny Tapeout 24-Pin Asynchronous FIFO.
    
    Pin Assignments:
      ui_in[7:0]  : wdata[7:0] (Write Data)
      uo_out[7:0] : rdata[7:0] (Read Data)
      uio_in[0]   : winc       (Write Enable)
      uio_in[1]   : rinc       (Read Enable)
      uio_in[2]   : wrst_n     (Write Domain Reset, Active-Low)
      uio_in[3]   : rrst_n     (Read Domain Reset, Active-Low)
      uio_in[4]   : wclk       (Write Clock)
      uio_in[5]   : rclk       (Read Clock)
      uio_out[6]  : wfull      (FIFO Full Flag)
      uio_out[7]  : rempty     (FIFO Empty Flag)
    """

    def __init__(self, dut):
        self.dut = dut
        self.wclk_task = None
        self.rclk_task = None

    def start_clocks(self, wclk_period_ns: float = 10.0, rclk_period_ns: float = 20.0):
        """Launches true concurrent, independent clock generators."""
        self.wclk_task = cocotb.start_soon(Clock(self.dut.wclk, wclk_period_ns, unit="ns").start())
        self.rclk_task = cocotb.start_soon(Clock(self.dut.rclk, rclk_period_ns, unit="ns").start())

    async def wait_wclk(self):
        """Waits for a rising edge on wclk."""
        await RisingEdge(self.dut.wclk)

    async def wait_rclk(self):
        """Waits for a rising edge on rclk."""
        await RisingEdge(self.dut.rclk)

    async def wait_wclk_cycles(self, n: int = 1):
        for _ in range(n):
            await RisingEdge(self.dut.wclk)

    async def wait_rclk_cycles(self, n: int = 1):
        for _ in range(n):
            await RisingEdge(self.dut.rclk)

    def get_flags(self):
        """Extracts wfull and rempty."""
        return int(self.dut.wfull.value), int(self.dut.rempty.value)

    async def reset(self):
        """Executes hardware reset on chip and both clock domains."""
        self.dut.ena.value = 1
        self.dut.clk.value = 0
        self.dut.rst_n.value = 0
        self.dut.ui_in.value = 0
        self.dut.wrst_n.value = 0
        self.dut.rrst_n.value = 0
        self.dut.winc.value = 0
        self.dut.rinc.value = 0

        # Hold reset across multiple clock cycles on both domains
        await self.wait_wclk_cycles(5)
        await self.wait_rclk_cycles(5)

        # Release resets (active-low)
        self.dut.rst_n.value = 1
        self.dut.wrst_n.value = 1
        self.dut.rrst_n.value = 1

        await self.wait_wclk_cycles(5)
        await self.wait_rclk_cycles(5)

    async def write_byte(self, data: int):
        """Writes one byte into the FIFO cleanly with setup/hold timing across edges."""
        await FallingEdge(self.dut.wclk)
        self.dut.ui_in.value = data & 0xFF
        self.dut.winc.value = 1
        await RisingEdge(self.dut.wclk)
        await FallingEdge(self.dut.wclk)
        self.dut.winc.value = 0

    async def read_byte(self) -> int:
        """Pops one byte from the FIFO cleanly with setup/hold timing across edges."""
        await FallingEdge(self.dut.rclk)
        self.dut.rinc.value = 1
        await RisingEdge(self.dut.rclk)
        await FallingEdge(self.dut.rclk)
        val = int(self.dut.uo_out.value)
        self.dut.rinc.value = 0
        return val


# ==============================================================================
# TEST 1: Power-On Reset & Initial Flag Verification
# ==============================================================================
@cocotb.test(timeout_time=100, timeout_unit="us")
async def test_reset_and_flags(dut):
    """Verifies power-on reset sequence and tri-state pin configuration."""
    dut._log.info("--- [TEST 1] Power-On Reset & Initial Flag Verification ---")
    tb = AsyncFIFOTester(dut)
    tb.start_clocks(wclk_period_ns=10.0, rclk_period_ns=20.0)
    await tb.reset()

    # Check tri-state output enable configuration (uio_oe must be 8'b1100_0000)
    oe_val = int(dut.uio_oe.value)
    assert oe_val == 0b11000000, f"FAIL: uio_oe expected 0b11000000, got 0b{oe_val:08b}"

    wfull, rempty = tb.get_flags()
    dut._log.info(f"Initial flags after reset: wfull={wfull}, rempty={rempty}")
    assert rempty == 1, "FAIL: FIFO must assert rempty after reset!"
    assert wfull == 0, "FAIL: FIFO must de-assert wfull after reset!"
    dut._log.info("[PASS] Test 1: Reset cleanly initializes FIFO.")


# ==============================================================================
# TEST 2: Single Byte Write & Read Loopback
# ==============================================================================
@cocotb.test(timeout_time=100, timeout_unit="us")
async def test_single_byte_loopback(dut):
    """Verifies single byte traversal through memory and synchronizer."""
    dut._log.info("--- [TEST 2] Single Byte Write & Read Loopback ---")
    tb = AsyncFIFOTester(dut)
    tb.start_clocks(wclk_period_ns=10.0, rclk_period_ns=20.0)
    await tb.reset()

    test_byte = 0xA5
    dut._log.info(f"Writing byte: 0x{test_byte:02X}")
    await tb.write_byte(test_byte)

    # Allow CDC synchronizer to propagate wptr to read domain (>= 3 rclk cycles)
    await tb.wait_rclk_cycles(6)

    wfull, rempty = tb.get_flags()
    assert rempty == 0, "FAIL: FIFO should NOT be empty after write!"
    assert wfull == 0, "FAIL: FIFO should not be full after 1 byte!"

    read_val = await tb.read_byte()
    dut._log.info(f"Read back byte: 0x{read_val:02X}")
    assert read_val == test_byte, f"FAIL: Data mismatch! Expected 0x{test_byte:02X}, got 0x{read_val:02X}"

    # Allow CDC synchronizer to propagate rptr back to write domain
    await tb.wait_wclk_cycles(6)
    wfull, rempty = tb.get_flags()
    assert rempty == 1, "FAIL: FIFO must return to empty after reading last byte!"
    assert wfull == 0, "FAIL: FIFO must not be full!"
    dut._log.info("[PASS] Test 2: Single byte loopback verified.")


# ==============================================================================
# TEST 3: Burst Write to Full Capacity (Depth = 16)
# ==============================================================================
@cocotb.test(timeout_time=100, timeout_unit="us")
async def test_burst_write_capacity(dut):
    """Verifies FIFO fills to depth 16 and asserts wfull without premature flag assertion."""
    dut._log.info("--- [TEST 3] Burst Write to Full Capacity (Depth = 16) ---")
    tb = AsyncFIFOTester(dut)
    tb.start_clocks(wclk_period_ns=10.0, rclk_period_ns=20.0)
    await tb.reset()

    test_data = [0x10 + i for i in range(16)]
    for i, byte_val in enumerate(test_data):
        wfull, _ = tb.get_flags()
        assert wfull == 0, f"FAIL: Premature wfull asserted at byte index {i}!"
        await tb.write_byte(byte_val)

    # Allow write clock cycles for flag register update
    await tb.wait_wclk_cycles(2)
    wfull, _ = tb.get_flags()
    assert wfull == 1, "FAIL: FIFO must assert wfull after writing 16 bytes!"

    # Allow CDC synchronizer cycles to propagate wptr to read domain
    await tb.wait_rclk_cycles(6)
    _, rempty = tb.get_flags()
    assert rempty == 0, "FAIL: FIFO should not be empty after 16 writes!"
    dut._log.info("[PASS] Test 3: Burst write filled FIFO to depth 16.")


# ==============================================================================
# TEST 4: Overflow Protection
# ==============================================================================
@cocotb.test(timeout_time=100, timeout_unit="us")
async def test_overflow_protection(dut):
    """Verifies write attempts on full FIFO are safely rejected by hardware without corruption."""
    dut._log.info("--- [TEST 4] Overflow Protection ---")
    tb = AsyncFIFOTester(dut)
    tb.start_clocks(wclk_period_ns=10.0, rclk_period_ns=20.0)
    await tb.reset()

    # Fill to capacity (16 bytes)
    for i in range(16):
        await tb.write_byte(0x30 + i)

    await tb.wait_wclk_cycles(2)
    wfull, _ = tb.get_flags()
    assert wfull == 1

    # Attempt to write extra byte into full FIFO
    dut._log.info("Attempting overflow write on full FIFO (must be blocked by hardware)...")
    await tb.write_byte(0xFF)

    await tb.wait_wclk_cycles(2)
    wfull, rempty = tb.get_flags()
    assert wfull == 1, "FAIL: wfull dropped after overflow attempt!"

    # Verify original 16 bytes were not corrupted
    await tb.wait_rclk_cycles(6)
    for i in range(16):
        val = await tb.read_byte()
        assert val == (0x30 + i), f"FAIL: Corrupted memory! Expected {0x30+i:#x}, got {val:#x}"

    dut._log.info("[PASS] Test 4: Overflow successfully blocked and memory preserved.")


# ==============================================================================
# TEST 5: Burst Read & Strict FIFO Ordering
# ==============================================================================
@cocotb.test(timeout_time=100, timeout_unit="us")
async def test_burst_read_ordering(dut):
    """Verifies strict First-In-First-Out ordering across a burst of 16 random bytes."""
    dut._log.info("--- [TEST 5] Burst Read & Strict FIFO Ordering ---")
    tb = AsyncFIFOTester(dut)
    tb.start_clocks(wclk_period_ns=10.0, rclk_period_ns=25.0)
    await tb.reset()

    test_pattern = [random.randint(0, 255) for _ in range(16)]
    dut._log.info(f"Writing 16 random bytes: {[hex(x) for x in test_pattern]}")
    for b in test_pattern:
        await tb.write_byte(b)

    await tb.wait_rclk_cycles(6)

    received = []
    for _ in range(16):
        val = await tb.read_byte()
        received.append(val)

    dut._log.info(f"Read back sequence: {[hex(x) for x in received]}")
    assert received == test_pattern, f"FAIL: FIFO ordering corrupted! Expected {test_pattern}, got {received}"

    await tb.wait_wclk_cycles(6)
    wfull, rempty = tb.get_flags()
    assert rempty == 1, "FAIL: FIFO should be empty after reading all 16 items!"
    assert wfull == 0, "FAIL: FIFO should not be full!"
    dut._log.info("[PASS] Test 5: All 16 bytes popped in exact First-In-First-Out order!")


# ==============================================================================
# TEST 6: Asynchronous CDC Stress Test (Fast Write 100MHz, Slow Read 30.3MHz)
# ==============================================================================
@cocotb.test(timeout_time=100, timeout_unit="us")
async def test_async_cdc_fast_write_slow_read(dut):
    """
    True CDC Concurrent Stress Test:
      Write Domain : 100.0 MHz (10.0 ns period)
      Read Domain  : ~30.3 MHz (33.0 ns period)
    Executes 40 concurrent randomized write and read transactions, verifying that
    the dual-clock FIFO safely crosses clock domains without dropping or corrupting data.
    """
    dut._log.info("--- [TEST 6] Asynchronous CDC: Fast Write (10ns) / Slow Read (33ns) ---")
    tb = AsyncFIFOTester(dut)
    tb.start_clocks(wclk_period_ns=10.0, rclk_period_ns=33.0)
    await tb.reset()

    num_items = 40
    written_data = []
    received_data = []

    async def writer_process():
        for i in range(num_items):
            while int(dut.wfull.value) == 1:
                await FallingEdge(dut.wclk)

            val = (0xA0 + i) & 0xFF
            written_data.append(val)
            await tb.write_byte(val)
            for _ in range(random.randint(0, 2)):
                await RisingEdge(dut.wclk)

    async def reader_process():
        for _ in range(num_items):
            while int(dut.rempty.value) == 1:
                await FallingEdge(dut.rclk)

            val = await tb.read_byte()
            received_data.append(val)
            for _ in range(random.randint(0, 2)):
                await RisingEdge(dut.rclk)

    w_task = cocotb.start_soon(writer_process())
    r_task = cocotb.start_soon(reader_process())

    await w_task
    await r_task

    assert received_data == written_data, (
        f"FAIL: CDC Data corruption! Sent {len(written_data)} items, received {len(received_data)} items."
    )
    dut._log.info(f"[PASS] Test 6: {num_items} items passed safely across 100MHz -> 30.3MHz domain!")


# ==============================================================================
# TEST 7: Asynchronous CDC Stress Test (Slow Write 30.3MHz, Fast Read 100MHz)
# ==============================================================================
@cocotb.test(timeout_time=100, timeout_unit="us")
async def test_async_cdc_slow_write_fast_read(dut):
    """
    True CDC Concurrent Stress Test:
      Write Domain : ~30.3 MHz (33.0 ns period)
      Read Domain  : 100.0 MHz (10.0 ns period)
    Verifies that a high-speed reader polling an empty FIFO safely waits for the slow writer
    without reading stale or duplicated data.
    """
    dut._log.info("--- [TEST 7] Asynchronous CDC: Slow Write (33ns) / Fast Read (10ns) ---")
    tb = AsyncFIFOTester(dut)
    tb.start_clocks(wclk_period_ns=33.0, rclk_period_ns=10.0)
    await tb.reset()

    num_items = 40
    written_data = []
    received_data = []

    async def writer_process():
        for i in range(num_items):
            while int(dut.wfull.value) == 1:
                await FallingEdge(dut.wclk)

            val = (0x50 + i) & 0xFF
            written_data.append(val)
            await tb.write_byte(val)
            for _ in range(random.randint(1, 3)):
                await RisingEdge(dut.wclk)

    async def reader_process():
        for _ in range(num_items):
            while int(dut.rempty.value) == 1:
                await FallingEdge(dut.rclk)

            val = await tb.read_byte()
            received_data.append(val)
            for _ in range(random.randint(0, 1)):
                await RisingEdge(dut.rclk)

    w_task = cocotb.start_soon(writer_process())
    r_task = cocotb.start_soon(reader_process())

    await w_task
    await r_task

    assert received_data == written_data, (
        f"FAIL: CDC Fast-Read corruption! Sent {len(written_data)} items, received {len(received_data)} items."
    )
    dut._log.info(f"[PASS] Test 7: {num_items} items passed safely across 30.3MHz -> 100MHz domain!")
