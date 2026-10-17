import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
const root=path.resolve(import.meta.dirname,'..');
const extension=path.join(root,'extension');
const manifest=JSON.parse(fs.readFileSync(path.join(extension,'manifest.json')));
for (const file of fs.readdirSync(extension).filter(x=>x.endsWith('.js'))) execFileSync(process.execPath,['--check',path.join(extension,file)]);
for (const file of [manifest.action.default_popup,manifest.background.service_worker,...Object.values(manifest.icons)]) {
  if (!fs.existsSync(path.join(extension,file))) throw new Error(`Missing manifest asset: ${file}`);
}
if (!manifest.key) throw new Error('Stable development key missing.');
if (manifest.host_permissions || manifest.content_scripts) throw new Error('This extension uses on-demand activeTab access only.');
if (manifest.permissions.includes('cookies')) throw new Error('Automatic browser cookie access must not be added.');
console.log('Extension syntax, assets, stable ID and permission boundaries verified.');
