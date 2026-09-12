let messages={};

function t(key,parameters={},fallback=key){
  const template=messages[key]??fallback;
  return Object.entries(parameters).reduce(
    (text,[name,value])=>text.replaceAll('{{'+name+'}}',String(value)),
    template,
  );
}

function applyTranslations(){
  document.querySelectorAll('[data-i18n]').forEach(element=>{
    element.textContent=t(element.dataset.i18n,{},element.textContent);
  });
  document.querySelectorAll('[data-i18n-aria-label]').forEach(element=>{
    element.setAttribute('aria-label',t(element.dataset.i18nAriaLabel,{},element.getAttribute('aria-label')));
  });
  document.querySelectorAll('[data-i18n-alt]').forEach(element=>{
    element.setAttribute('alt',t(element.dataset.i18nAlt,{},element.getAttribute('alt')));
  });
}

async function initializeI18n(){
  const locale=navigator.languages?.find(language=>language.toLowerCase().startsWith('pt'))?'pt-BR':'en';
  document.documentElement.lang=locale;
  if(locale!=='en'){
    try{
      const response=await fetch('/fleet/assets/locales/'+locale+'.json');
      if(response.ok)messages=await response.json();
    }catch{}
  }
  applyTranslations();
}

window.t=t;
window.i18nReady=initializeI18n();
