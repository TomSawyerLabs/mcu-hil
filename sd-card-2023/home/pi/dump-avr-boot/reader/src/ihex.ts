import { EOL } from "os";

enum RecordType {
  Data = 0,
  EndOfFile = 1,
  ExtendedSegmentAddress = 2,
  StartSegmentAddress = 3,
  ExtendedLinearAddress = 4,
  StartLinearAddress = 5,
}

class Record {
  private constructor(public address: number, public data: Buffer, public type: RecordType) {}
  static makeDataRecord(address: number, data: Buffer) {
    return new Record(address, data, RecordType.Data);
  }
  static makeEndOfFileRecord() {
    return new Record(0, Buffer.alloc(0), RecordType.EndOfFile);
  }
  toString() {
    const out = Buffer.concat([
      Buffer.from([this.data.length, this.address >> 8, this.address & 0xff, this.type]),
      this.data,
      Buffer.from([0]), // Checksum placeholder. 0 doesn't change the calculation.
    ]);

    // Checksum
    out[out.length - 1] = -out.reduce((a, b) => a + b, 0);

    return `:${out.toString("hex").toUpperCase()}${EOL}`;
  }
}

type Options = {
  filterEmptyLines?: boolean;
  emptyByte?: number;
  bytesPerLine?: number;
};

export class IntelHex {
  private records: Record[] = [];

  constructor(data?: Buffer, address = 0, options?: Options) {
    if (data) this.addData(data, address, options);
  }

  addData(data: Buffer, address = 0, options?: Options) {
    const filterEmptyLines = options?.filterEmptyLines ?? true;
    const emptyByte = options?.emptyByte ?? 0xff;
    const bytesPerLine = options?.bytesPerLine ?? 1 << 5;

    if (bytesPerLine < 1) throw new Error("bytesPerLine must be >= 1");
    if (data.length > bytesPerLine) {
        const opts = {filterEmptyLines, emptyByte, bytesPerLine}
      this.addData(data.subarray(0, bytesPerLine), address, opts);
      this.addData(data.subarray(bytesPerLine), address + bytesPerLine, opts);
      return;
    }

    if (filterEmptyLines) {
        let empty = true;
        for (const byte of data) {
            if (byte !== emptyByte) {
                empty = false;
                break;
            }
        }
        if (empty) return;
    }

    this.records.push(Record.makeDataRecord(address, data));
  }

  toString() {
    let ret = "";
    for (const record of this.records) ret += record.toString();
    ret += Record.makeEndOfFileRecord().toString();
    return ret;
  }
}
