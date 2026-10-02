# ==============================================================================
# Tiny Tapeout Cocotb Testbench for tt_um_fifo
# Asynchronous Dual-Clock FIFO Hardware & CDC Verification Suite
# ==============================================================================

import cocotb
from cocotb.triggers import Timer, RisingEdge, ClockCycles
import random


class FIFOTestHelper:
    """Helper class to control the 24-pin Tiny Tapeout interface for tt_um_fifo."""
    def __init__(self, dut):
        self.dut = dut
        self.winc = 0
        self.rinc = 0
        self.wrst_n = 1
        self.rrst_n = 1
        self.wclk = 0
        self.rclk = 0

    def _update_uio(self):
        """Packs individual control and clock signals into the 8-bit uio_in bus."""
        val = (
            (self.winc & 1)   << 0 |
            (self.rinc & 1)   << 1 |
            (self.wrst_n & 1) << 2 |
            (self.rrst_n & 1) << 3 |
            (self.wclk & 1)   << 4 |
            (self.rclk & 1)   << 5
        )
        self.dut.uio_in.value = val

    async def pulse_wclk(self):
        """Generates a clean rising and falling edge on wclk (Pin uio[4])."""
        self.wclk = 1
        self._update_uio()
        await Timer(10, units="ns")
        self.wclk = 0
        self._update_uio()
        await Timer(10, units="ns")

    async def pulse_rclk(self):
        """Generates a clean rising and falling edge on rclk (Pin uio[5])."""
        self.rclk = 1
        self._update_uio()
        await Timer(10, units="ns")
        self.rclk = 0
        self._update_uio()
        await Timer(10, units="ns")

    def get_flags(self):
        """Extracts wfull (uio[6]) and rempty (uio[7]) from uio_out bus."""
        uio_val = int(self.dut.uio_out.value)
        wfull = (uio_val >> 6) & 1
        rempty = (uio_val >> 7) & 1
        return wfull, rempty

    async def reset(self):
        """Executes full power-on reset sequence."""
        self.dut._log.info("Asserting power-on reset...")
        self.dut.ena.value = 1
        self.dut.clk.value = 0
        self.dut.rst_n.value = 0
        self.dut.ui_in.value = 0
        self.wrst_n = 0
        self.rrst_n = 0
        self.winc = 0
        self.rinc = 0
        self._update_uio()

        for _ in range(5):
            await self.pulse_wclk()
            await self.pulse_rclk()

        self.dut.rst_n.value = 1
        self.wrst_n = 1
        self.rrst_n = 1
        self._update_uio()

        for _ in range(5):
            await self.pulse_wclk()
            await self.pulse_rclk()

    async def write_byte(self, byte_val):
        """Writes one byte into FIFO on wclk, then cycles rclk for CDC synchronizer."""
        self.dut.ui_in.value = byte_val & 0xFF
        self.winc = 1
        self._update_uio()
        await self.pulse_wclk()
        self.winc = 0
        self._update_uio()

        # Background read clock cycles for 2-stage CDC synchronizer
        for _ in range(4):
            await self.pulse_rclk()

    async def read_byte(self):
        """Reads one byte from FIFO on rclk, then cycles wclk for CDC synchronizer."""
        self.rinc = 1
        self._update_uio()
        await self.pulse_rclk()
        self.rinc = 0
        self._update_uio()

        val = int(self.dut.uo_out.value)

        # Background write clock cycles for 2-stage CDC synchronizer
        for _ in range(4):
            await self.pulse_wclk()

        return val


# ==============================================================================
# TEST 1: Power-On Reset & Initial Flag Verification
# ==============================================================================
@cocotb.test()
async def test_reset_and_flags(dut):
    dut._log.info("--- [TEST 1] Power-On Reset & Initial Flag Verification ---")
    fifo = FIFOTestHelper(dut)
    await fifo.reset()

    # Check tri-state output enable configuration (uio_oe must be 8'b1100_0000)
    oe_val = int(dut.uio_oe.value)
    assert oe_val == 0b11000000, f"FAIL: uio_oe expected 0b11000000, got 0b{oe_val:08b}"

    wfull, rempty = fifo.get_flags()
    dut._log.info(f"Initial flags after reset: wfull={wfull}, rempty={rempty}")
    assert rempty == 1, "FAIL: FIFO must be EMPTY after reset!"
    assert wfull == 0, "FAIL: FIFO must NOT be FULL after reset!"
    dut._log.info("[PASS] Test 1: Reset cleanly initializes FIFO.")


# ==============================================================================
# TEST 2: Single Byte Write & Read Loopback
# ==============================================================================
@cocotb.test()
async def test_single_byte_loopback(dut):
    dut._log.info("--- [TEST 2] Single Byte Write & Read Loopback ---")
    fifo = FIFOTestHelper(dut)
    await fifo.reset()

    test_byte = 0xA5
    dut._log.info(f"Writing byte: 0x{test_byte:02X}")
    await fifo.write_byte(test_byte)

    wfull, rempty = fifo.get_flags()
    dut._log.info(f"Flags after single write: wfull={wfull}, rempty={rempty}")
    assert rempty == 0, "FAIL: FIFO should NOT be empty after write!"
    assert wfull == 0, "FAIL: FIFO should not be full after 1 byte!"

    read_val = await fifo.read_byte()
    dut._log.info(f"Read back byte: 0x{read_val:02X}")
    assert read_val == test_byte, f"FAIL: Data mismatch! Expected 0x{test_byte:02X}, got 0x{read_val:02X}"

    wfull, rempty = fifo.get_flags()
    dut._log.info(f"Flags after read: wfull={wfull}, rempty={rempty}")
    assert rempty == 1, "FAIL: FIFO must be empty after popping last byte!"
    dut._log.info("[PASS] Test 2: Single byte loopback verified.")


# ==============================================================================
# TEST 3: Burst Write to Full Capacity (Depth = 16)
# ==============================================================================
@cocotb.test()
async def test_burst_write_capacity(dut):
    dut._log.info("--- [TEST 3] Burst Write to Full Capacity (Depth = 16) ---")
    fifo = FIFOTestHelper(dut)
    await fifo.reset()

    test_pattern = [0x10 + i for i in range(16)]
    for idx, b in enumerate(test_pattern):
        wfull, _ = fifo.get_flags()
        assert wfull == 0, f"FAIL: Premature wfull at byte {idx}!"
        await fifo.write_byte(b)

    wfull, rempty = fifo.get_flags()
    dut._log.info(f"Flags after 16 writes: wfull={wfull}, rempty={rempty}")
    assert wfull == 1, "FAIL: FIFO must assert wfull after 16 writes!"
    assert rempty == 0, "FAIL: FIFO should not be empty after 16 writes!"
    dut._log.info("[PASS] Test 3: Burst write filled FIFO to depth 16.")


# ==============================================================================
# TEST 4: Overflow Protection
# ==============================================================================
@cocotb.test()
async def test_overflow_protection(dut):
    dut._log.info("--- [TEST 4] Overflow Protection ---")
    fifo = FIFOTestHelper(dut)
    await fifo.reset()

    # Fill to full
    for i in range(16):
        await fifo.write_byte(0x20 + i)

    wfull, _ = fifo.get_flags()
    assert wfull == 1

    # Attempt write on full FIFO
    dut._log.info("Attempting write on full FIFO (must be blocked)...")
    await fifo.write_byte(0xFF)

    wfull, rempty = fifo.get_flags()
    assert wfull == 1, "FAIL: FIFO dropped full flag after overflow attempt!"
    assert rempty == 0, "FAIL: FIFO became empty unexpectedly!"

    # Verify original 16 bytes were not corrupted
    for i in range(16):
        val = await fifo.read_byte()
        assert val == (0x20 + i), f"FAIL: Memory corrupted by overflow! Expected {0x20+i:#x}, got {val:#x}"

    dut._log.info("[PASS] Test 4: Overflow attempt successfully blocked and data preserved.")


# ==============================================================================
# TEST 5: Burst Read & Strict FIFO Ordering
# ==============================================================================
@cocotb.test()
async def test_burst_read_ordering(dut):
    dut._log.info("--- [TEST 5] Burst Read & Strict FIFO Ordering ---")
    fifo = FIFOTestHelper(dut)
    await fifo.reset()

    test_pattern = [random.randint(0, 255) for _ in range(16)]
    dut._log.info(f"Writing 16 random bytes: {[hex(x) for x in test_pattern]}")
    for b in test_pattern:
        await fifo.write_byte(b)

    received = []
    for _ in range(16):
        val = await fifo.read_byte()
        received.append(val)

    dut._log.info(f"Read back sequence: {[hex(x) for x in received]}")
    assert received == test_pattern, f"FAIL: Data order mismatch! Expected {test_pattern}, got {received}"

    wfull, rempty = fifo.get_flags()
    assert rempty == 1, "FAIL: FIFO should be empty after reading all 16 items!"
    assert wfull == 0, "FAIL: FIFO should not be full after reading!"
    dut._log.info("[PASS] Test 5: All 16 bytes popped in exact First-In-First-Out order!")
