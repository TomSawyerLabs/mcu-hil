#!/usr/bin/node
import { parseFile } from "./parser";
import { reader } from "./reader";

export async function main(args: string[]) {
  const [command] = args;
  switch (command) {
    default:
      console.error("Unknown command:", command);
      process.exitCode = 1;
      return;
    case undefined:
    case "read":
      return reader();
    case "parse":
      return parseFile(args[1]);
  }
}

if (require.main === module) {
  main(process.argv.slice(2)).catch((e) => {
    console.error('Uncaught Error:');
    console.error(e);
    // Set exit code to 2, for 'graceful' error exit
    process.exitCode = 2;

    setTimeout(() => {
      // Force exit after 1 second
      console.error("Somthing was still running... forcing exit");
      process.exit(99);
    }, 1000).unref();
  });
}
