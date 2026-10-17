import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
const root=path.resolve(import.meta.dirname,'..');
const extension=path.join(root,'extension');
const manifest=JSON.parse(fs.readFileSync(path.join(root,'manifest.json')));
for (const file of fs.readdirSync(extension).filter(x=>x.endsWith('.js'))) execFileSync(process.execPath,['--check',path.join(extension,file)]);
for (const file of [manifest.action.default_popup,manifest.background.service_worker,...Object.values(manifest.icons)]) {
  if (!fs.existsSync(path.join(root,file))) throw new Error(`Missing manifest asset: ${file}`);
}
if (!manifest.key) throw new Error('Stable development key missing.');
if (manifest.host_permissions || manifest.content_scripts) throw new Error('This extension uses on-demand activeTab access only.');
if (manifest.permissions.includes('cookies')) throw new Error('Automatic browser cookie access must not be added.');
console.log('Extension syntax, assets, stable ID and permission boundaries verified.');
const vendors=JSON.parse(fs.readFileSync(path.join(root,'tools/runtime-manifest.json'),'utf8'));
for(const name of ['python','node','ffmpeg','pip']) {
  if(!vendors[name]?.url.startsWith('https://') || !/^[a-f0-9]{64}$/.test(vendors[name].sha256))throw new Error(`Missing verified runtime archive: ${name}`);
}
