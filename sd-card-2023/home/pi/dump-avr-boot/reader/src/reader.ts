import { SerialPort } from "serialport";
import { Gpio } from "pigpio";

function makeWatchdog(ms: number): Promise<void> & { tick: (timeoutMs?: number) => void } {
  let timeout: NodeJS.Timeout;
  let resolver: () => void;

  function tick(newTimeout?: number) {
    if (newTimeout) ms = newTimeout;
    clearTimeout(timeout);
    timeout = setTimeout(resolver, ms);
  }

  const p = new Promise<void>((resolve) => {
    resolver = resolve;
  });

  tick();

  return Object.assign(p, { tick });
}

export async function reader() {
  const port = new SerialPort({ path: "/dev/serial0", baudRate: 1e6 / 8, autoOpen: false });
  const commDisable = new Gpio(8, { mode: Gpio.OUTPUT });
  commDisable.digitalWrite(0);

  // const final = Buffer.allocUnsafe(0x2000);
  // let index = 0;
  // function append(next: Buffer) {
  //   final.set(next, index);
  //   index += next.length;
  // }

  await new Promise<void>((resolve, reject) => port.open((err) => (err ? reject(err) : resolve())));

  const timeout = makeWatchdog(1500);

  port.on("data", (data: Buffer) => {
    timeout.tick();

    console.log(data.toString("hex"));
  });

  // Tell AVR to send all the data
  port.write(" ");

  await new Promise<void>((resolve, reject) => port.drain((err) => (err ? reject(err) : resolve())));

  await timeout;

  port.close();
}
