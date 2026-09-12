(function renderRecentCaptures(){
  const source=document.getElementById('encounters');
  const target=document.getElementById('captures');
  if(!source||!target)return;
  const update=()=>{
    target.replaceChildren(...Array.from(source.children)
      .filter(item=>item.classList.contains('captured'))
      .map(item=>item.cloneNode(true)));
    if(!target.children.length){
      const empty=document.createElement('small');
      empty.textContent=window.t?.('no_captures',{},'No captures recorded.')||'No captures recorded.';
      target.append(empty);
    }
  };
  new MutationObserver(update).observe(source,{childList:true});
  update();
})();
