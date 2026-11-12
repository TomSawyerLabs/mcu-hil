import { pins } from "./pins";
import { Gpio } from "pigpio";
import { delay } from "./utils";

export async function reset(runBootloader = true): Promise<void> {
  const rst = new Gpio(pins.Reset);
  const hwb = new Gpio(pins.HWB);

  hwb.mode(Gpio.OUTPUT);
  rst.mode(Gpio.OUTPUT);

  rst.digitalWrite(0);
  hwb.digitalWrite(runBootloader ? 0 : 1);

  await delay(100);

  rst.digitalWrite(1);

  await delay(100);

  hwb.mode(Gpio.INPUT);
}

export async function driveClock(
  frequency: number | false = 16e6
): Promise<void> {
  const clock = new Gpio(pins.Clock);
  const enable = new Gpio(pins.ClockEnable);

  enable.mode(Gpio.OUTPUT);
  if (!frequency) {
    console.log("Clock drive disabled");
    enable.digitalWrite(0);
    return;
  }

  console.log("Enabling clock driver");
  clock.hardwareClockWrite(frequency);
  enable.digitalWrite(1);
}
