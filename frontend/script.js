const tabs=document.querySelectorAll('nav button');
const sections=document.querySelectorAll('.tab');

tabs.forEach(btn=>btn.addEventListener('click',()=>{
  sections.forEach(sec=>sec.classList.remove('active'));
  document.getElementById(btn.dataset.tab).classList.add('active');
}));

async function fetchJSON(url){
  const res=await fetch(url);
  return res.json();
}

document.getElementById('searchBtn').addEventListener('click',async()=>{
  const q=document.getElementById('query').value;
  const data=await fetchJSON(`/api/search?q=${encodeURIComponent(q)}`);
  document.getElementById('searchResult').textContent=JSON.stringify(data,null,2);
});

async function loadInboxes(){
  const data=await fetchJSON('/api/inbox/list');
  const select=document.getElementById('emailInbox');
  data.inboxes.forEach(addr=>{
    const opt=document.createElement('option');
    opt.value=addr;opt.textContent=addr;select.appendChild(opt);
  });
}
loadInboxes();

document.getElementById('loadEmails').addEventListener('click',async()=>{
  const inboxSelect=document.getElementById('emailInbox');
  const selected=[...inboxSelect.selectedOptions].map(o=>o.value).join(',');
  const cat=document.getElementById('emailCategory').value;
  const data=await fetchJSON(`/api/emails?inboxes=${encodeURIComponent(selected)}&category=${encodeURIComponent(cat)}`);
  const ul=document.getElementById('emailList');
  ul.innerHTML='';
  data.emails.forEach(e=>{
    const li=document.createElement('li');
    li.textContent=`${e.date} - ${e.subject}`;
    ul.appendChild(li);
  });
});

document.getElementById('loadDocs').addEventListener('click',async()=>{
  const type=document.getElementById('docType').value;
  const cat=document.getElementById('docCategory').value;
  const data=await fetchJSON(`/api/documents?source_type=${encodeURIComponent(type)}&category=${encodeURIComponent(cat)}`);
  const ul=document.getElementById('docList');
  ul.innerHTML='';
  data.documents.forEach(d=>{
    const li=document.createElement('li');
    li.textContent=`${d.doc_metadata.filename || 'doc'} - ${d.category}`;
    ul.appendChild(li);
  });
});

let queueOffset=0;
async function loadQueue(){
  const data=await fetchJSON(`/api/processing_queue/list?offset=${queueOffset}&limit=10`);
  const ul=document.getElementById('queueList');
  ul.innerHTML='';
  data.items.forEach(item=>{
    const li=document.createElement('li');
    li.textContent=`${item.created_at} - ${item.item_type} - ${item.status}`;
    ul.appendChild(li);
  });
}
document.getElementById('nextPage').addEventListener('click',()=>{queueOffset+=10;loadQueue();});
document.getElementById('prevPage').addEventListener('click',()=>{queueOffset=Math.max(0,queueOffset-10);loadQueue();});
loadQueue();
