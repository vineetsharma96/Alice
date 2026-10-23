
function showMemory(){
 const packet=window.AliceMood,box=document.getElementById('memory-summary');
 if(!packet?.person?.emotional_memory||!box)return;
 const m=packet.person.emotional_memory,r=packet.retrieval;
 box.textContent=`Private emotional memory: ${m.entries.length}/32 links retained; ${m.encoded} encoded, ${m.evicted} evicted. Mode: ${m.mode}. Current context: ${r.context}; expectation ${r.value.toFixed(3)}, support ${r.confidence.toFixed(3)} from ${r.memories.length} relevant links. Weights and routing are authored; experiences are acquired. Eviction does not erase the factual journal.`;
 document.getElementById('mood-evidence').textContent=JSON.stringify({memory:m,retrieval:r,last:packet.person.last,source:packet.origin},null,2);
 window.AliceMemory=packet;
}
setInterval(showMemory,1500);
