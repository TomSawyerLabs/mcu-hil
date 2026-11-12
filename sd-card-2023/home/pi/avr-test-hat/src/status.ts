import { Gpio } from "pigpio";
import { access, readFile } from "fs/promises";
import { pins } from "./pins";
import { exec } from "child_process";
import { measure } from "pi-temperature";

namespace BCM {
  export type PinNumber = number;
  export type PinMode = "in" | "out" | "alt0" | "alt1" | "alt2" | "alt3" | "alt4" | "alt5";
}

class PinStatus {
  constructor(public mode: BCM.PinMode, public value: 0 | 1) {}
}

class SysFSStatus extends PinStatus {
  toString() {
    return `${this.mode.padEnd(4)} ${this.value ? "🟢" : "🔴"}`;
  }
}

function prettyFreqyency(frequency: number, fixedPrecision = 0) {
  if (frequency <= 0) return "";
  if (frequency < 1e3) return `${frequency.toFixed(fixedPrecision)}  Hz`;
  if (frequency < 1e6) return `${(frequency / 1e3).toFixed(fixedPrecision)} kHz`;
  return `${(frequency / 1e6).toFixed(fixedPrecision)} MHz`;
}

class PiGPIOStatus extends PinStatus {
  constructor(mode: BCM.PinMode, value: 0 | 1, public frequency: number) {
    super(mode, value);
  }
  toString() {
    return `${this.mode.padStart(4)} ${this.value ? "🟢" : "🔴"}  ${prettyFreqyency(this.frequency).padStart(7)}`;
  }
}

type SysFSFiles = "value" | "direction";

function getSysFsGPIOPath(pin: BCM.PinNumber, file?: SysFSFiles) {
  let ret = `/sys/class/gpio/gpio${pin}`;
  if (file) ret += `/${file}`;
  return ret;
}

async function readSysFsGPIO(pin: BCM.PinNumber): Promise<boolean>;
async function readSysFsGPIO(pin: BCM.PinNumber, file: "value"): Promise<0 | 1>;
async function readSysFsGPIO(pin: BCM.PinNumber, file: "direction"): Promise<BCM.PinMode>;
async function readSysFsGPIO(pin: BCM.PinNumber, file?: SysFSFiles): Promise<BCM.PinMode | boolean | 0 | 1> {
  const path = getSysFsGPIOPath(pin, file);
  if (!file) {
    return access(path).then(
      () => true,
      () => false
    );
  }

  const reading = (await readFile(path)).toString().trim();
  switch (file) {
    case "value":
      switch (reading) {
        case "0":
          return 0;
        case "1":
          return 1;
        default:
          throw new Error(`Unknown value: ${reading}`);
      }
    case "direction":
      switch (reading) {
        case "in":
        case "input":
          return "in";
        case "out":
        case "output":
          return "out";
        default:
          throw new Error(`Unknown direction: ${reading}`);
      }
  }
}

async function getSysFsStatus(pin: BCM.PinNumber): Promise<undefined | PinStatus> {
  const direction = readSysFsGPIO(pin, "direction");
  const value = readSysFsGPIO(pin, "value");
  try {
    return new SysFSStatus(...(await Promise.all([direction, value])));
  } catch (e) {
    return undefined;
  }
}

function PiGPIOModeToStatus(mode: number) {
  switch (mode) {
    case Gpio.INPUT:
      return "in";
    case Gpio.OUTPUT:
      return "out";
    case Gpio.ALT0:
      return "alt0";
    case Gpio.ALT1:
      return "alt1";
    case Gpio.ALT2:
      return "alt2";
    case Gpio.ALT3:
      return "alt3";
    case Gpio.ALT4:
      return "alt4";
    case Gpio.ALT5:
      return "alt5";
    default:
      throw new Error(`Unknown PiGPIO mode: ${mode}`);
  }
}

async function getPiGPIOStatus(pin: BCM.PinNumber): Promise<PiGPIOStatus> {
  const gpio = new Gpio(pin);
  const direction = gpio.getMode();
  const value = gpio.digitalRead() as 0 | 1;
  const frequency = gpio.getPwmFrequency();
  return new PiGPIOStatus(PiGPIOModeToStatus(direction), value, frequency);
}

type GPIOStatus = {
  SysFS?: SysFSStatus;
  PiGPIO: PiGPIOStatus;
};

async function getGPIOStatus(pin: BCM.PinNumber): Promise<GPIOStatus> {
  const [SysFS, PiGPIO] = await Promise.all([getSysFsStatus(pin), getPiGPIOStatus(pin)]);
  return { SysFS, PiGPIO };
}

export type Status = {
  active: boolean;

  gpio: {
    active: GPIOStatus;
    reset: GPIOStatus;
    resetPull: GPIOStatus;
    HWB: GPIOStatus;
    HWBPull: GPIOStatus;
    VCC: GPIOStatus;
    UVCC: GPIOStatus;
    Clock: GPIOStatus;
    ClockEnable: GPIOStatus;
    SPIDisable: GPIOStatus;
    SerialDisable: GPIOStatus;
  };

  // dfu device connected?
  usb: boolean;

  // Degrees C
  temperature: number;
};

export async function getStatus(): Promise<Status> {
  const active = isActive();
  const gpio = {
    active: getGPIOStatus(pins.ActivityLED),
    reset: getGPIOStatus(pins.Reset),
    resetPull: getGPIOStatus(pins.ResetPull),
    HWB: getGPIOStatus(pins.HWB),
    HWBPull: getGPIOStatus(pins.HWBPull),
    VCC: getGPIOStatus(pins.VCC),
    UVCC: getGPIOStatus(pins.UVCC),
    Clock: getGPIOStatus(pins.Clock),
    ClockEnable: getGPIOStatus(pins.ClockEnable),
    SPIDisable: getGPIOStatus(pins.SPIDisable),
    SerialDisable: getGPIOStatus(pins.SerialDisable),
  };
  const connected = isDeviceConnected();
  const temperature = new Promise<number>((resolve, reject) =>
    measure((err, temp) => (err ? reject(err) : resolve(temp!)))
  );

  active.then(_ => console.log('Active done'))
  Promise.all(Object.values(gpio)).then(() => console.log('Gpio done'))
  connected.then(_ => console.log('Active done'))
  temperature.then(_ => console.log('Temperature done'))


  // If multiple async calls fail simultaneously, if we don't await them all, we'll only get the first error and the rest will be "unhandled".
  await Promise.all([active, ...Object.values(gpio), connected, temperature]);

  return {
    active: await active,
    gpio: {
      active: await gpio.active,
      reset: await gpio.reset,
      resetPull: await gpio.resetPull,
      HWB: await gpio.HWB,
      HWBPull: await gpio.HWBPull,
      VCC: await gpio.VCC,
      UVCC: await gpio.UVCC,
      Clock: await gpio.Clock,
      ClockEnable: await gpio.ClockEnable,
      SPIDisable: await gpio.SPIDisable,
      SerialDisable: await gpio.SerialDisable,
    },
    usb: await connected,
    temperature: await temperature,
  };
}

export async function isActive(): Promise<boolean> {
  return readSysFsGPIO(pins.ActivityLED);
}

export async function isDeviceConnected(): Promise<boolean> {
  return new Promise((resolve, reject) => {
    console.log('isDeviceConnected')
    exec("lsusb", (error, stdout, stderr) => {
      console.log('isDeviceConnected.exec')
      if (error) {
        return reject(error);
      }
      if (stderr) {
        return reject(stderr);
      }
      let ret = false;
      if (stdout.includes("ID 03eb:2ff7 Atmel Corp. at90usb82 DFU bootloader")) ret = true;
      if (stdout.includes("ID 03eb:2fee Atmel Corp. atmega8u2 DFU bootloader")) ret = true;
      resolve(ret);
    });
  });
}
