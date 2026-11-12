import { readFile } from "fs/promises";
import { IntelHex } from "./ihex";

export async function parseFile(path: string) {
  const text = await readFile(path);

  const data = Buffer.from(text.toString().replace(/\s/g, ""), "hex");

  const ihex = new IntelHex(data);

  console.log(ihex.toString());
}
