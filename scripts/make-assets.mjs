import fs from 'node:fs';
import path from 'node:path';
import {generateKeyPairSync} from 'node:crypto';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const root=path.resolve(import.meta.dirname,'..');
const file=path.join(root,'manifest.json');
const manifest=JSON.parse(fs.readFileSync(file));
if (!manifest.key) {const {publicKey}=generateKeyPairSync('rsa',{modulusLength:2048});manifest.key=publicKey.export({type:'spki',format:'der'}).toString('base64');fs.writeFileSync(file,JSON.stringify(manifest,null,2)+'\n');}
const sharp=require(process.env.VIDEO_TOOLS_SHARP || 'sharp');
const svg=fs.readFileSync(path.join(root,'favicon.svg'),'utf8');
const dir=path.join(root,'extension','icons');fs.mkdirSync(dir,{recursive:true});
fs.writeFileSync(path.join(dir,'source.svg'),svg);
for(const size of [16,32,48,128])await sharp(Buffer.from(svg)).resize(size,size).png().toFile(path.join(dir,`${size}.png`));
console.log('Stable public manifest key and icons ready; no private key is stored.');
