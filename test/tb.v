/*
 * Copyright (c) 2026 Shlomo Abrams
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none
`timescale 1ns / 1ps

/* This testbench just instantiates the module and makes some convenient wires
   that can be driven / tested by the cocotb test.py.
*/
module tb ();

  // Dump the signals to a FST file. You can view it with gtkwave or surfer.
  initial begin
    $dumpfile("tb.fst");
    $dumpvars(0, tb);
    #1;
  end

  // Wire up the inputs and outputs:
  reg clk;
  reg rst_n;
  reg ena;
  reg [7:0] ui_in;
  reg wclk;
  reg rclk;
  reg winc;
  reg rinc;
  reg wrst_n;
  reg rrst_n;
  wire [7:0] uio_in = {2'b00, rclk, wclk, rrst_n, wrst_n, rinc, winc};
  wire [7:0] uo_out;
  wire [7:0] uio_out;
  wire [7:0] uio_oe;

  // Single-bit aliases for Cocotb edge triggers & waveform inspection
  wire wfull  = uio_out[6];
  wire rempty = uio_out[7];
`ifdef GL_TEST
  wire VPWR = 1'b1;
  wire VGND = 1'b0;
`endif

  initial begin
    clk    = 1'b0;
    rst_n  = 1'b0;
    ena    = 1'b1;
    ui_in  = 8'h00;
    wclk   = 1'b0;
    rclk   = 1'b0;
    winc   = 1'b0;
    rinc   = 1'b0;
    wrst_n = 1'b0;
    rrst_n = 1'b0;
  end

  // Replace tt_um_example with your module name:
  tt_um_shlomo_fifo user_project (

      // Include power ports for the Gate Level test:
`ifdef GL_TEST
      .VPWR(VPWR),
      .VGND(VGND),
`endif

      .ui_in  (ui_in),    // Dedicated inputs
      .uo_out (uo_out),   // Dedicated outputs
      .uio_in (uio_in),   // IOs: Input path
      .uio_out(uio_out),  // IOs: Output path
      .uio_oe (uio_oe),   // IOs: Enable path (active high: 0=input, 1=output)
      .ena    (ena),      // enable - goes high when design is selected
      .clk    (clk),      // clock
      .rst_n  (rst_n)     // not reset
  );

endmodule
