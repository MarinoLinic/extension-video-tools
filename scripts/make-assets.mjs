import fs from 'node:fs';
import path from 'node:path';
import {generateKeyPairSync} from 'node:crypto';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const root=path.resolve(import.meta.dirname,'..');
const file=path.join(root,'extension','manifest.json');
const manifest=JSON.parse(fs.readFileSync(file));
if (!manifest.key) {const {publicKey}=generateKeyPairSync('rsa',{modulusLength:2048});manifest.key=publicKey.export({type:'spki',format:'der'}).toString('base64');fs.writeFileSync(file,JSON.stringify(manifest,null,2)+'\n');}
const sharp=require(process.env.VIDEO_TOOLS_SHARP || 'sharp');
const svg='<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128"><rect width="128" height="128" rx="28" fill="#bce9c3"/><path d="M64 27v51m-20-20 20 21 20-21M32 88v14h64V88" stroke="#193121" stroke-width="9" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>';
const dir=path.join(root,'extension','icons');fs.mkdirSync(dir,{recursive:true});
fs.writeFileSync(path.join(dir,'source.svg'),svg);
for(const size of [16,32,48,128])await sharp(Buffer.from(svg)).resize(size,size).png().toFile(path.join(dir,`${size}.png`));
console.log('Stable public manifest key and icons ready; no private key is stored.');
