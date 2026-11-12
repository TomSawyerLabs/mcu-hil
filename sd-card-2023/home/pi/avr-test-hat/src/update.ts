import { exec } from "child_process";

export async function getUpgrades(): Promise<string[]> {
    return new Promise ((resolve, reject) => {
      exec('apt-get -qq --simulate upgrade -o APT::Get::Show-User-Simulation-Note=false', (err, stdout, stderr) => {
        if (err) return reject(err);
        const lines = stdout.split('\n');
        const upgrades = lines.filter(line => line.startsWith('Inst '));
        resolve(upgrades);
      });
    });
  }