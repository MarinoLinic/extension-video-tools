import test from 'node:test';
import assert from 'node:assert/strict';
import {parseTime,formatTime,validRange,canonicalVideoUrl,clipRequest,DEFAULTS} from '../extension/core.js';
test('exact time entry preserves subsecond values for long videos',()=>{
  assert.equal(parseTime('1:02:50.250'),3770.25);assert.equal(parseTime('2:50'),170);
  assert.equal(parseTime('170.125'),170.125);assert.equal(formatTime(3770.25),'1:02:50.25');
  for(const text of ['','2:60','1:99:00','-2','Infinity','1.2345','abc'])assert.ok(Number.isNaN(parseTime(text)),text);
  assert.equal(formatTime(59.9999),'1:00');
});
test('clip boundaries reject reversals and values beyond the source',()=>{
  assert.ok(validRange(170,180,7200));assert.ok(validRange(0,null,null));
  for(const values of [[10,10,100],[10,5,100],[-1,5,100],[100,null,100],[0,101,100],[NaN,null,100]])assert.equal(validRange(...values),false);
});
test('a full-length selection stays a full download and ignores playlist/timestamp URL hints',()=>{
  assert.equal(canonicalVideoUrl('https://www.youtube.com/watch?v=BaW_jenozKc&list=PL123&t=20'),'https://www.youtube.com/watch?v=BaW_jenozKc');
  const request=clipRequest({url:'https://example.com/video',title:'Test',duration:100},{start:0,end:100},DEFAULTS);
  assert.equal(request.end,null);assert.equal(request.mode,'video');
  assert.equal(clipRequest({url:'https://example.com/v',duration:7200},{start:170.25,end:180.75},DEFAULTS).start,170.25);
  assert.throws(()=>clipRequest({url:'file:///secret'},{start:0,end:null},DEFAULTS));
});
