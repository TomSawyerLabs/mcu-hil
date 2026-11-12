#!/usr/bin/node
import { getStatus } from "./status";
import { reset, driveClock } from "./control";

export async function status() {
  const { active, gpio, usb, temperature } = await getStatus();

  console.log(`Pi Temperature is ${temperature.toFixed(1)} °C${temperature > 60 ? " 🔥" : ""}`);
  console.log(`Activity GPIO: ${active ? "Busy 🟡" : "Inactive 🟢"}`);

  const longestNameLength = Object.keys(gpio).reduce((longest, name) => Math.max(longest, name.length), 0);

  let name: keyof typeof gpio;
  for (name in gpio) {
    const { PiGPIO, SysFS } = gpio[name];
    console.log(`GPIO ${name.padEnd(longestNameLength)}: ${PiGPIO.toString()}${SysFS ? ` (SysFS)` : ""}`);
  }
  console.log(`USB DFU bootloader is: ${usb ? "Connected ✅" : "Disconnected ❌"}`);
  
}

export async function main(args: string[]) {
  switch (args[0]) {
    case undefined:
    case "status":
      return status();
    case "reset":
      return reset(args[1] === 'boot');
    case "clock":
      return driveClock(args[1] ? parseInt(args[1]) : undefined);
  }
}

if (require.main === module) {
  main(process.argv.slice(2)).catch((e) => {
    console.error(e);
    // Set exit code to 1, for 'graceful' error exit
    process.exitCode = 1;

    setTimeout(() => {
      // Force exit after 1 second
      process.exit(2);
    }, 1000).unref();
  });
}
