var DataSpeakAIWidget=(function(_e){"use strict";var v,Te,j,Me,Z,Ae,ee,Pe,ue,fe,te={},ae=[],et=/^m(i|n|o|s|text|space)$/,he=Array.isArray,be=ae.slice,O=Object.assign;function ne(t){t&&t.parentNode&&t.remove()}function u(t,e,a){var n,o,s,r={},l=arguments.length;for(s in e)s=="key"?n=e[s]:s=="ref"&&typeof t!="function"?o=e[s]:r[s]=e[s];return l>2&&(r.children=l>3?be.call(arguments,2):a),J(t,r,n,o,null)}function J(t,e,a,n,o){var s={type:t,props:e,key:a,ref:n,__k:null,__:null,__b:0,__e:null,__c:null,constructor:void 0,__v:o||++Te,__i:-1,__u:0};return!o&&v.vnode&&v.vnode(s),s}function se(t){return t.children}function oe(t,e){this.props=t,this.context=e,this.__g=0}function L(t,e){if(e==null)return t.__?L(t.__,t.__i+1):null;for(var a;e<t.__k.length;e++)if((a=t.__k[e])&&a.__e)return a.__e;return typeof t.type!="function"||t.props.__P?null:L(t)}function Ie(t){if((t=t.__)&&t.__c&&!t.props.__P)return t.__e=null,t.__k.some(function(e){return e&&(t.__e=e.__e)}),Ie(t)}function De(t){(8&t.__g||!(t.__g|=8)||!j.push(t)||Z++)&&Me==v.debounceRendering||((Me=v.debounceRendering)||queueMicrotask)(tt)}function tt(){var t,e,a,n,o,s,r,l,d;try{for(e=1;j.length;)j.length>e&&j.sort(Ae),t=j.shift(),e=j.length,8&t.__g&&(n=void 0,o=void 0,s=(o=(a=t).__v).__e,r=[],l=[],(d=a.__P)&&((n=O({constructor:void 0},o)).__v=o.__v+1,v.vnode&&v.vnode(n),ge(d,n,o,a.__n,d.namespaceURI,32&o.__u?[s]:null,r,s||L(o),32&o.__u,l),n.__v=o.__v,n.__.__k[n.__i]=n,Ne(r,n,l),o.__=o.__e=null,n.__e!=s&&Ie(n)))}finally{j.length=Z=0}}function Ee(t,e,a,n,o,s,r,l,d,_,c){var g,h,b,f,i,w,k=n.__k||ae,S=e.length;for(d=at(a,e,k,d,S),g=0;g<S;g++)(b=a.__k[g])!=null&&(h=~b.__i&&k[b.__i]||te,b.__i=g,w=ge(t,b,h,o,s,r,l,d,_,c),f=b.__e,(h.ref!=b.ref||8&h.__u)&&(h.ref&&me(h.ref,null,b,h),b.ref&&c.push(b.ref,b.__c||f,b)),i=i||f,4&b.__u?(d=ze(b,d,t,!h.__v),h.__e&&(h.__e=null)):typeof b.type=="function"&&w!==void 0?d=w:f&&(d=f.nextSibling),b.__u&=-7);return a.__e=i,d}function at(t,e,a,n,o){var s,r,l,d,_,c,g,h,b,f,i=a.length,w=i,k=0,S=!1,m=t.__k=Array(o);for(s=0;s<o;s++)(r=e[s])!=null&&typeof r!="boolean"&&typeof r!="function"?(typeof r!="object"||r.constructor==String?r=m[s]=J(null,r):he(r)?r=m[s]=J(se,{children:r}):r.constructor===void 0&&r.__b?r=m[s]=J(r.type,r.props,r.key,r.ref,r.__v):m[s]=r,d=s+k,r.__=t,r.__b=t.__b+1,l=null,~(_=r.__i=nt(r,a,d,w))&&(w--,(l=a[_])&&(l.__u|=2)),l&&l.__v?(r.__u|=2,_==d-1?k--:_==d+1?k++:_!=d&&(_>d?k--:k++,S=!0)):(~_||(o>i?k--:o<i&&k++),typeof r.type!="function"&&(r.__u|=4))):m[s]=null;if(S){for(c=[],g=[],s=0;s<o;s++)if((r=m[s])&&2&r.__u){for(h=0,b=c.length;h<b;)c[f=h+b>>1]<r.__i?h=f+1:b=f;c[h]=r.__i,g[s]=h+1}for(k=c.length;s--;)g[s]&&(g[s]==k?k--:m[s].__u|=4)}if(w)for(s=0;s<i;s++)!(l=a[s])||2&l.__u||(l.__e==n&&(n=L(l)),xe(l,l));return n}function ze(t,e,a,n){var o,s,r;if(typeof t.type=="function"){if(t.props.__P)return e;if(o=t.__k)for(s=0;s<o.length;s++)o[s]&&(o[s].__=t,e=ze(o[s],e,a,!1));return e}for(e&&!e.parentNode&&(e=L(t))&&!e.parentNode&&(e=null),r=e;r&&r.nodeType==8;)r=r.nextSibling;for(t.__e!=r&&(!n&&a.moveBefore&&t.__e.parentNode?a.moveBefore(t.__e,e):a.insertBefore(t.__e,e||null)),e=t.__e;(e=e&&e.nextSibling)&&e.nodeType==8;);return e}function nt(t,e,a,n){var o,s,r,l=t.key,d=t.type,_=e[a],c=_&&!(2&_.__u);if(_===null&&l==null||c&&l==_.key&&d==_.type)return a;if(n>(c?1:0)){for(o=a-1,s=a+1;o>=0||s<e.length;)if((_=e[r=o>=0?o--:s++])&&!(2&_.__u)&&l==_.key&&d==_.type)return r}return-1}function He(t,e,a){a==null&&(a=""),e[0]=="-"?t.setProperty(e,a):t[e]=a}function re(t,e,a,n,o){var s,r;e:if(e=="style")if(typeof a=="string")t.style.cssText=a;else{if(typeof n=="string"&&(t.style.cssText=n=""),n)for(e in n)a&&e in a||He(t.style,e,"");if(a)for(e in a)n&&a[e]==n[e]||He(t.style,e,a[e])}else if(e[0]=="o"&&e[1]=="n")(t.__e||(t.__e={}))[e]=a,a&&n||(r=fe[e]||(fe[e]=st(e)),(t.__a||(t.__a={}))[e]=ue,s=e!=(e=e.replace(Pe,"$1")),(e=e.slice(2))[0]<"a"&&(e=e.toLowerCase()),a?t.addEventListener(e,r,s):t.removeEventListener(e,r,s));else{if(o=="http://www.w3.org/2000/svg")e=e.replace(/xlink(H|:h)/,"h").replace(/sName$/,"s");else if(e!="width"&&e!="height"&&e!="href"&&e!="list"&&e!="form"&&e!="tabIndex"&&e!="download"&&e!="rowSpan"&&e!="colSpan"&&e!="role"&&e!="popover"&&e in t)try{t[e]=a??"";break e}catch{}typeof a=="function"||(a==null||a===!1&&e[4]!="-"?t.removeAttribute(e):t.setAttribute(e,e=="popover"&&a==1?"":a))}}function st(t){return function(e){if(this.__e){var a=this.__e[t];if(e[ee]==null)e[ee]=ue++;else if(e[ee]<this.__a[t])return;return a(v.event?v.event(e):e)}}}function ge(t,e,a,n,o,s,r,l,d,_){var c,g,h,b,f,i,w,k,S,m,x,$,z,B,pe,U,F,q,H,A,D=e.type;if(e.constructor!==void 0)return null;if(128&a.__u&&(d=32&a.__u,c=a.__c.__z)){if(e.__u|=d,g=s=[],c.nodeType==8)for(h=1,b=c.nextSibling;b;b=b.nextSibling){if(b.nodeType==8){if(b.data.startsWith("$s"))h++;else if(b.data.startsWith("/$s")&&!--h)break}s.push(b)}else s.push(c);l=s[0]}(c=v.__b)&&c(e);e:if(typeof D=="function"){f=r.length;try{if(m=e.props,x=(c=D.prototype)&&c.render,$=(c=D.contextType)&&n[c.__c],z=c?$?$.props.value:c.__:n,a.__c?2&(i=e.__c=a.__c).__g&&(i.__g|=1):(x?e.__c=i=new D(m,z):(e.__c=i=new oe(m,z),i.constructor=D,i.render=rt),$&&$.sub(i),i.state||(i.state={}),i.__n=n,i.__g|=8,i.__h=[],i.__k=[]),x&&(i.__s||(i.__s=i.state),D.getDerivedStateFromProps&&(i.__s==i.state&&(i.__s=O({},i.__s)),O(i.__s,D.getDerivedStateFromProps(m,i.__s)))),w=i.props,k=i.state,i.__v=e,a.__c){if(x&&!D.getDerivedStateFromProps&&m!==w&&i.componentWillReceiveProps&&i.componentWillReceiveProps(m,z),e.__v==a.__v&&!(8&i.__g)||!(4&i.__g)&&i.shouldComponentUpdate&&i.shouldComponentUpdate(m,i.__s,z)===!1){e.__v!=a.__v&&(i.props=m,i.state=i.__s,i.__g&=-9),e.__e=a.__e,e.__k=a.__k,e.__k.some(function(p){p&&(p.__=e)}),ae.push.apply(i.__h,i.__k),i.__k=[],i.__h.length&&r.push(i),l=L(a);break e}i.componentWillUpdate&&i.componentWillUpdate(m,i.__s,z),x&&i.componentDidUpdate&&i.__h.push(function(){i.componentDidUpdate(w,k,S)})}else x&&!D.getDerivedStateFromProps&&i.componentWillMount&&i.componentWillMount(),x&&i.componentDidMount&&i.__h.push(i.componentDidMount);if(i.context=z,i.props=m,i.__P=t,i.__g&=-5,B=v.__r,pe=0,x)i.state=i.__s,i.__g&=-9,B&&B(e),c=i.render(i.props,i.state,i.context),ae.push.apply(i.__h,i.__k),i.__k=[];else do i.__g&=-9,B&&B(e),c=i.render(i.props,i.state,i.context),i.state=i.__s;while(8&i.__g&&++pe<25);i.state=i.__s,i.getChildContext&&(n=O({},n,i.getChildContext())),x&&a.__c&&i.getSnapshotBeforeUpdate&&(S=i.getSnapshotBeforeUpdate(w,k)),U=c&&c.type===se&&c.key==null?c.props.children:c,m.__P&&(c=l,o=(t=m.__P).namespaceURI,d=s=null,a.props&&a.props.__P!=t&&(a.__k.some(function(p){p&&xe(p,p)}),a.__k=null),l=a.__k?L(a,0):null),l=Ee(t,he(U)?U:[U],e,a,n,o,s,r,l,d,_),m.__P&&(e.__e=null,l=c),e.__u&=-161,128&a.__u&&(i.__z=null),g&&g.some(ne),i.__h.length&&r.push(i),1&i.__g&&(i.__g&=-4)}catch(p){if(r.length=f,e.__v=null,d||s)if(p.then){if(F=0,e.__u|=d?160:128,s){for(~(H=s.indexOf(l||void 0))||(H=s.length);(A=s[H-1])&&A.nodeType==8;)H--;for(;H<s.length;H++)if(A=s[H]){if(s[H]=null,A.nodeType==8){if(A.data.startsWith("$s"))F++||(q=A);else if(F&&A.data.startsWith("/$s")&&!--F){l=A;break}}else if(!F)break}}if(!q){for(;l&&l.nodeType==8&&l.nextSibling;)l=l.nextSibling;q=l}e.__c.__z||(e.__c.__z=q),e.__e=l}else s&&s.some(ne);else e.__e=a.__e;e.__k||(e.__k=a.__k||[]),p.then||Ce(e),v.__e(p,e,a)}}else l=e.__e=ot(a.__e,e,a,n,o,s,r,d,_,t);return(c=v.diffed)&&c(e),128&e.__u?void 0:l}function Ce(t){t&&(t.__c&&(t.__c.__g|=4),t.__k&&t.__k.some(Ce))}function Ne(t,e,a){for(var n=0;n<a.length;)me(a[n++],a[n++],a[n++]);v.__c&&v.__c(e,t),t.some(function(o){try{t=o.__h,o.__h=[],t.some(function(s){s.call(o)})}catch(s){v.__e(s,o.__v)}})}function ot(t,e,a,n,o,s,r,l,d,_){var c,g,h,b,f,i,w,k,S,m=a.props||te,x=e.props,$=e.type;if($=="svg"?o="http://www.w3.org/2000/svg":$=="math"?o="http://www.w3.org/1998/Math/MathML":o||(o="http://www.w3.org/1999/xhtml"),s){for(c=0;c<s.length;c++)if((f=s[c])&&($?f.localName==$:f.nodeType==3)){t=f,s[c]=null;break}}if(!t){if(k=_.ownerDocument||document,!$)return k.createTextNode(x);t=k.createElementNS(o,$,x.is&&x),l&&(v.__m&&v.__m(e,s),l=!1),s=null}if($){if(_=$=="template"?t.content:t,s=$=="textarea"&&x.defaultValue!=null?null:s&&be.call(_.childNodes),!l&&s)for(m={},c=0;c<t.attributes.length;c++)m[(f=t.attributes[c]).name]=f.value;for(c in m)f=m[c],c=="dangerouslySetInnerHTML"?h=f:c=="children"||c in x||c=="value"&&"defaultValue"in x||c=="checked"&&"defaultChecked"in x||re(t,c,null,f,o);for(c in S=1&a.__u,x)f=x[c],c=="children"?b=f:c=="dangerouslySetInnerHTML"?g=f:c=="value"?i=f:c=="checked"?w=f:l&&typeof f!="function"||!(m[c]!==f||S&&f!=null)||re(t,c,f,m[c],o);g?(l||h&&(g.__html==h.__html||g.__html==t.innerHTML)||(t.innerHTML=g.__html),e.__k=[]):(h&&(t.textContent=""),($=="foreignObject"||o=="http://www.w3.org/1998/Math/MathML"&&et.test($))&&(o="http://www.w3.org/1999/xhtml"),Ee(_,he(b)?b:[b],e,a,n,o,s,r,s?s[0]:a.__k&&L(a,0),l,d),s&&s.some(ne)),l&&$!="textarea"||(c="value",$=="progress"&&i==null?t.removeAttribute(c):i==null||i===t[c]&&($!="progress"||i)||re(t,c,i,m[c],o),c="checked",w!=null&&w!=t[c]&&re(t,c,w,m[c],o))}else m===x||l&&t.data==x||(t.data=x);return t}function me(t,e,a,n){try{typeof t=="function"?e?e.__x=t(e)||1:n&&(n=n.__c||n.__e)&&(e=n.__x)&&(n.__x=null,typeof e=="function"?e():t(null)):t.current=e}catch(o){v.__e(o,a)}}function xe(t,e,a){var n,o;if(v.unmount&&v.unmount(t),!(n=t.ref)||n.current&&n.current!=t.__e||me(n,null,e,t),n=t.__c){if(n.componentWillUnmount)try{n.componentWillUnmount()}catch(s){v.__e(s,e)}n.__P=n.__n=null}if(n=t.__k)for(o=0;o<n.length;o++)n[o]&&xe(n[o],e,typeof t.type!="function"||a&&!t.props.__P);(n=t.__e)&&(a||ne(n),n.__e&&(n.__e=null)),t.__e=t.__c=t.__=null}function rt(t,e,a){return this.constructor(t,a)}function je(t,e){var a,n,o,s;v.__&&v.__(t,e),e.nodeType==9&&(e=e.documentElement),n=(a=t&&32&t.__u)?null:e.__k,e.__k=J(se,{children:[t]}),o=[],s=[],ge(e,e.__k,n||te,te,e.namespaceURI,n?null:e.firstChild?be.call(e.childNodes):null,o,n?n.__e:e.firstChild,a,s),Ne(o,e.__k,s),e.__k.props.children=null}v={__e:function(t,e,a,n){for(var o,s,r;e=e.__;)if((o=e.__c)&&!(1&o.__g)){o.__g|=4;try{if((s=o.constructor)&&s.getDerivedStateFromError&&(o.setState(s.getDerivedStateFromError(t)),r=8&o.__g),o.componentDidCatch&&(o.componentDidCatch(t,n||{}),r=8&o.__g),r)return void(o.__g|=2)}catch(l){t=l,r=0}}throw Z=0,t}},Te=0,oe.prototype.setState=function(t,e){var a=this.__s;a&&a!=this.state||(a=this.__s=O({},this.state)),typeof t=="function"&&(t=t(O({},a),this.props)),t&&(O(a,t),this.__v&&(e&&this.__k.push(e),De(this)))},oe.prototype.forceUpdate=function(t){this.__v&&(this.__g|=4,t&&this.__h.push(t),De(this))},oe.prototype.render=se,j=[],Z=0,Ae=function(t,e){return t.__v.__b-e.__v.__b},ee=Symbol(),Pe=/(PointerCapture)$|Capture$/i,ue=0,fe={};const ie="dataspeak_widget_";function it(t){try{const e=localStorage.getItem(`${ie}${t}`);if(!e)return null;const a=JSON.parse(e);return Date.now()>a.expiresAt-6e4?(localStorage.removeItem(`${ie}${t}`),null):a}catch{return null}}function lt(t,e){try{localStorage.setItem(`${ie}${t}`,JSON.stringify(e))}catch{}}function ct(t){try{localStorage.removeItem(`${ie}${t}`)}catch{}}async function dt(t,e,a){const n=`${t.replace(/\/+$/,"")}/api/widget/session`,o=await fetch(n,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({public_key:e,conversation_id:a})});if(!o.ok){let l="Failed to initialize session";try{l=(await o.json()).detail||l}catch{}throw new Error(l)}const s=await o.json(),r={sessionToken:s.session_token,expiresAt:Date.now()+s.expires_in*1e3,tenantId:s.tenant_id,conversationId:s.conversation_id};return lt(e,r),r}async function pt(t,e){try{const a=`${t.replace(/\/+$/,"")}/api/widget/config?key=${encodeURIComponent(e)}`,n=await fetch(a);if(!n.ok)return{};const o=await n.json();return{themeColor:o.theme_color,widgetTitle:o.widget_title,greetingMessage:o.greeting_message,position:o.position,welcomeDelay:o.welcome_delay,soundEnabled:o.sound_enabled}}catch{return{}}}function Le(t){const e=t.trim();if(!e.startsWith("data:"))return null;const a=e.slice(5).trim();if(!a||a==="[DONE]")return null;try{return JSON.parse(a)}catch{return null}}class _t{constructor(){this.buffer=""}feed(e){this.buffer+=e;const a=this.buffer.split(`

`);this.buffer=a.pop()||"";const n=[];for(const o of a){const s=Le(o);s&&n.push(s)}return n}flush(){if(!this.buffer.trim())return[];const e=Le(this.buffer);return this.buffer="",e?[e]:[]}}async function ut(t,e,a,n,o,s,r,l){const d=`${t.replace(/\/+$/,"")}/api/chat/widget`;try{const _=await fetch(d,{method:"POST",signal:l,headers:{"Content-Type":"application/json",Authorization:`Bearer ${e}`,Accept:"text/event-stream"},body:JSON.stringify({query:a,session_token:e,conversation_id:n,stream:!0})});if(_.status===429){const f=_.headers.get("Retry-After"),i=f?parseInt(f,10):5;let w="Too many requests. Please wait before asking again.";try{const k=await _.json();k.detail&&(w=k.detail)}catch{}r(w,i);return}if(!_.ok){let f="Failed to send message";try{const i=await _.json();i.detail&&(f=i.detail)}catch{}r(f);return}if(!_.body){r("No response received from assistant");return}const c=_.body.getReader(),g=new TextDecoder("utf-8"),h=new _t;for(;;){if(l!=null&&l.aborted){try{await c.cancel()}catch{}return}const{done:f,value:i}=await c.read();if(f)break;const w=g.decode(i,{stream:!0}),k=h.feed(w);for(const S of k)S.error&&r(S.error),S.chunk&&o(S.chunk),S.done&&s({conversationId:S.conversation_id||n,messageId:S.message_id,sources:S.sources||[]})}const b=h.flush();for(const f of b)f.error&&r(f.error),f.chunk&&o(f.chunk),f.done&&s({conversationId:f.conversation_id||n,messageId:f.message_id,sources:f.sources||[]})}catch(_){if(_.name==="AbortError"||l!=null&&l.aborted)return;r(_.message||"Network connection error")}}function le(t="#3b82f6",e="bottom-right"){const a=e==="bottom-left",n=a?"left: 20px;":"right: 20px;";return`
:host {
  all: initial;
  position: fixed;
  visibility: visible !important;
  z-index: 2147483647;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  font-size: 14px;
  line-height: 1.5;
  color-scheme: light dark;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;

  --ds-theme: ${t};
  --ds-bg: #ffffff;
  --ds-bg-soft: #f6f7fb;
  --ds-text: #111827;
  --ds-text-soft: #6b7280;
  --ds-border: #e5e7eb;
  --ds-bubble-bot: #ffffff;
  --ds-bubble-bot-text: #1f2937;
  --ds-shadow: 0 20px 50px rgba(15, 23, 42, 0.18), 0 4px 12px rgba(15, 23, 42, 0.08);
}

@media (prefers-color-scheme: dark) {
  :host {
    --ds-bg: #111827;
    --ds-bg-soft: #0b1220;
    --ds-text: #f3f4f6;
    --ds-text-soft: #9ca3af;
    --ds-border: #1f2937;
    --ds-bubble-bot: #1f2937;
    --ds-bubble-bot-text: #f3f4f6;
    --ds-shadow: 0 20px 50px rgba(0, 0, 0, 0.6), 0 4px 12px rgba(0, 0, 0, 0.4);
  }
}

.dataspeak-container { visibility: visible !important; }

*, *::before, *::after {
  box-sizing: border-box !important;
  margin: 0;
  padding: 0;
  font-family: inherit;
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

/* ---------- Launcher ---------- */
.dataspeak-launcher {
  position: fixed;
  bottom: 20px;
  ${n}
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--ds-theme), color-mix(in srgb, var(--ds-theme) 70%, #000));
  color: #fff;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 24px color-mix(in srgb, var(--ds-theme) 45%, transparent), 0 2px 6px rgba(0,0,0,.15);
  transition: transform .25s cubic-bezier(.34,1.56,.64,1), box-shadow .25s ease;
  z-index: 2147483647;
  outline: none;
}
.dataspeak-launcher::after {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 2px solid var(--ds-theme);
  opacity: 0;
  animation: ds-pulse 2.6s ease-out infinite;
  pointer-events: none;
}
.dataspeak-launcher.is-open::after { animation: none; }
.dataspeak-launcher:hover { transform: scale(1.08) rotate(-4deg); }
.dataspeak-launcher:active { transform: scale(.96); }
.dataspeak-launcher:focus-visible { outline: 3px solid #93c5fd; outline-offset: 3px; }
.dataspeak-launcher svg { width: 26px; height: 26px; }

@keyframes ds-pulse {
  0%   { transform: scale(1);   opacity: .55; }
  70%  { transform: scale(1.45); opacity: 0; }
  100% { transform: scale(1.45); opacity: 0; }
}

/* ---------- Panel ---------- */
.dataspeak-panel {
  position: fixed;
  bottom: 92px;
  ${n}
  width: 384px;
  max-width: calc(100vw - 32px);
  height: 600px;
  max-height: calc(100dvh - 116px);
  background: var(--ds-bg);
  color: var(--ds-text);
  border-radius: 20px;
  box-shadow: var(--ds-shadow);
  border: 1px solid var(--ds-border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  z-index: 2147483647;
  opacity: 0;
  visibility: hidden;
  transform: translateY(20px) scale(.96);
  transform-origin: ${a?"bottom left":"bottom right"};
  pointer-events: none;
  transition: opacity .25s ease, transform .3s cubic-bezier(.16,1,.3,1), visibility .25s;
}
.dataspeak-panel.open {
  opacity: 1;
  visibility: visible;
  transform: translateY(0) scale(1);
  pointer-events: auto;
}

@media (max-width: 480px) {
  .dataspeak-panel {
    inset: 0 !important;
    width: 100% !important;
    height: 100dvh !important;
    max-width: 100% !important;
    max-height: 100dvh !important;
    border-radius: 0 !important;
    border: none !important;
  }
}

/* ---------- Header ---------- */
.dataspeak-header {
  padding: 16px 16px 16px 18px;
  background: linear-gradient(135deg, var(--ds-theme), color-mix(in srgb, var(--ds-theme) 65%, #000));
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  position: relative;
}
.dataspeak-header::after {
  content: "";
  position: absolute;
  inset: auto 0 0 0;
  height: 1px;
  background: rgba(255,255,255,.18);
}
.dataspeak-header-left { display: flex; align-items: center; gap: 12px; }
.dataspeak-avatar {
  width: 38px; height: 38px;
  border-radius: 12px;
  background: rgba(255,255,255,.2);
  backdrop-filter: blur(6px);
  border: 1px solid rgba(255,255,255,.28);
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 13px; letter-spacing: .5px;
}
.dataspeak-header-title { font-weight: 650; font-size: 15.5px; line-height: 1.2; }
.dataspeak-header-status {
  font-size: 11.5px; opacity: .92;
  display: flex; align-items: center; gap: 5px; margin-top: 2px;
}
.dataspeak-status-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: #34d399;
  box-shadow: 0 0 0 0 rgba(52,211,153,.7);
  animation: ds-online 2s infinite;
}
@keyframes ds-online {
  0% { box-shadow: 0 0 0 0 rgba(52,211,153,.6); }
  70% { box-shadow: 0 0 0 6px rgba(52,211,153,0); }
  100% { box-shadow: 0 0 0 0 rgba(52,211,153,0); }
}
.dataspeak-header-actions { display: flex; gap: 2px; }
.dataspeak-icon-btn {
  background: transparent; border: none; color: #fff; cursor: pointer;
  padding: 8px; border-radius: 10px; display: flex;
  align-items: center; justify-content: center;
  opacity: .85; transition: opacity .15s, background-color .15s, transform .15s;
}
.dataspeak-icon-btn:hover { opacity: 1; background: rgba(255,255,255,.18); }
.dataspeak-icon-btn:active { transform: scale(.92); }
.dataspeak-icon-btn:focus-visible { outline: 2px solid #fff; outline-offset: 1px; }

/* ---------- Messages ---------- */
.dataspeak-messages {
  flex: 1;
  overflow-y: auto;
  padding: 18px 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  background: var(--ds-bg-soft);
  scroll-behavior: smooth;
}
.dataspeak-messages::-webkit-scrollbar { width: 6px; }
.dataspeak-messages::-webkit-scrollbar-thumb { background: var(--ds-border); border-radius: 3px; }
.dataspeak-messages::-webkit-scrollbar-thumb:hover { background: var(--ds-text-soft); }

.dataspeak-msg-row {
  display: flex; flex-direction: column; max-width: 86%;
  animation: ds-in .28s cubic-bezier(.16,1,.3,1) both;
}
@keyframes ds-in {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
.dataspeak-msg-row.user { align-self: flex-end; align-items: flex-end; }
.dataspeak-msg-row.assistant { align-self: flex-start; align-items: flex-start; }

.dataspeak-bubble {
  padding: 11px 15px;
  font-size: 13.8px;
  line-height: 1.5;
  word-break: break-word;
  overflow-wrap: anywhere;
}
.dataspeak-msg-row.user .dataspeak-bubble {
  background: linear-gradient(135deg, var(--ds-theme), color-mix(in srgb, var(--ds-theme) 78%, #000));
  color: #fff;
  border-radius: 18px 18px 4px 18px;
  box-shadow: 0 3px 10px color-mix(in srgb, var(--ds-theme) 30%, transparent);
}
.dataspeak-msg-row.assistant .dataspeak-bubble {
  background: var(--ds-bubble-bot);
  color: var(--ds-bubble-bot-text);
  border: 1px solid var(--ds-border);
  border-radius: 18px 18px 18px 4px;
  box-shadow: 0 1px 3px rgba(0,0,0,.05);
}

.dataspeak-time {
  font-size: 10.5px; color: var(--ds-text-soft);
  margin-top: 4px; padding: 0 4px;
}

/* ---------- Sources ---------- */
.dataspeak-sources { margin-top: 7px; display: flex; flex-wrap: wrap; gap: 5px; }
.dataspeak-source-badge {
  font-size: 11px; font-weight: 500;
  background: color-mix(in srgb, var(--ds-theme) 12%, transparent);
  color: var(--ds-theme);
  padding: 3px 8px; border-radius: 999px;
  display: inline-flex; align-items: center; gap: 3px;
  border: 1px solid color-mix(in srgb, var(--ds-theme) 25%, transparent);
}

/* ---------- Quick replies ---------- */
.dataspeak-chips { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 4px; }
.dataspeak-chip {
  background: var(--ds-bg);
  color: var(--ds-theme);
  border: 1px solid color-mix(in srgb, var(--ds-theme) 40%, transparent);
  padding: 7px 13px; border-radius: 999px;
  font-size: 12.5px; font-weight: 500; cursor: pointer;
  transition: all .18s ease;
}
.dataspeak-chip:hover {
  background: var(--ds-theme); color: #fff;
  transform: translateY(-1px);
  box-shadow: 0 4px 10px color-mix(in srgb, var(--ds-theme) 35%, transparent);
}

/* ---------- Typing ---------- */
.dataspeak-typing {
  display: flex; align-items: center; gap: 5px;
  padding: 12px 15px; background: var(--ds-bubble-bot);
  border: 1px solid var(--ds-border);
  border-radius: 18px 18px 18px 4px; width: fit-content;
}
.dataspeak-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--ds-text-soft);
  animation: ds-bounce 1.3s infinite ease-in-out both;
}
.dataspeak-dot:nth-child(1) { animation-delay: -.3s; }
.dataspeak-dot:nth-child(2) { animation-delay: -.15s; }
@keyframes ds-bounce {
  0%, 80%, 100% { transform: translateY(0); opacity: .4; }
  40% { transform: translateY(-5px); opacity: 1; }
}

/* ---------- Error ---------- */
.dataspeak-error-banner {
  padding: 9px 14px;
  background: #fef2f2; color: #b91c1c;
  border-top: 1px solid #fecaca;
  font-size: 12px;
  display: flex; align-items: center; justify-content: space-between;
  animation: ds-in .2s ease both;
}
.dataspeak-countdown { font-weight: 700; }

/* ---------- Footer ---------- */
.dataspeak-footer {
  padding: 12px 14px 10px;
  background: var(--ds-bg);
  border-top: 1px solid var(--ds-border);
  flex-shrink: 0;
}
.dataspeak-input-row { display: flex; align-items: flex-end; gap: 8px; }
.dataspeak-input {
  flex: 1;
  border: 1.5px solid var(--ds-border);
  border-radius: 22px;
  padding: 9px 16px;
  font-size: 13.8px; line-height: 1.4;
  outline: none; resize: none;
  max-height: 110px; min-height: 40px;
  color: var(--ds-text);
  background: var(--ds-bg-soft);
  transition: border-color .15s, box-shadow .15s, background .15s;
}
.dataspeak-input::placeholder { color: var(--ds-text-soft); }
.dataspeak-input:focus {
  border-color: var(--ds-theme);
  background: var(--ds-bg);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--ds-theme) 18%, transparent);
}
.dataspeak-input:disabled { opacity: .6; cursor: not-allowed; }

.dataspeak-send-btn, .dataspeak-stop-btn {
  width: 40px; height: 40px; border-radius: 50%;
  color: #fff; border: none; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  transition: transform .15s, opacity .15s, box-shadow .15s;
}
.dataspeak-send-btn {
  background: linear-gradient(135deg, var(--ds-theme), color-mix(in srgb, var(--ds-theme) 70%, #000));
  box-shadow: 0 4px 12px color-mix(in srgb, var(--ds-theme) 35%, transparent);
}
.dataspeak-send-btn:disabled { opacity: .4; cursor: not-allowed; box-shadow: none; }
.dataspeak-send-btn:not(:disabled):hover { transform: scale(1.08); }
.dataspeak-send-btn:not(:disabled):active { transform: scale(.94); }
.dataspeak-stop-btn { background: #ef4444; box-shadow: 0 4px 12px rgba(239,68,68,.35); }
.dataspeak-stop-btn:hover { background: #dc2626; transform: scale(1.08); }

.dataspeak-branding {
  text-align: center; font-size: 10.5px;
  color: var(--ds-text-soft); margin-top: 8px;
}
.dataspeak-branding a { color: var(--ds-text-soft); text-decoration: none; font-weight: 600; }
.dataspeak-branding a:hover { color: var(--ds-theme); }

/* ---------- Markdown ---------- */
.dataspeak-bubble p { margin-bottom: 8px; }
.dataspeak-bubble p:last-child { margin-bottom: 0; }
.dataspeak-bubble strong { font-weight: 650; }
.dataspeak-bubble em { font-style: italic; }
.dataspeak-bubble h1, .dataspeak-bubble h2, .dataspeak-bubble h3 {
  font-size: 14.5px; font-weight: 650; margin: 8px 0 4px;
}
.dataspeak-bubble code {
  background: color-mix(in srgb, var(--ds-text) 8%, transparent);
  padding: 2px 5px; border-radius: 4px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px;
}
.dataspeak-bubble pre {
  background: #0f172a; color: #e2e8f0;
  padding: 10px 12px; border-radius: 10px;
  overflow-x: auto; margin: 6px 0; font-size: 12px;
}
.dataspeak-bubble pre code { background: none; padding: 0; color: inherit; }
.dataspeak-bubble a { color: var(--ds-theme); text-decoration: underline; word-break: break-all; }
.dataspeak-bubble ul, .dataspeak-bubble ol { margin: 4px 0 8px 20px; }
.dataspeak-bubble li { margin-bottom: 3px; }
`}function ft(t="#3b82f6",e="bottom-right"){const a=document.createElement("div");a.id="dataspeak-chatbot-widget-root",a.style.setProperty("display","block","important"),a.style.setProperty("visibility","visible","important"),a.style.setProperty("position","fixed","important"),a.style.setProperty("z-index","2147483647","important"),a.style.setProperty("border","none","important"),a.style.setProperty("margin","0","important"),a.style.setProperty("padding","0","important"),a.style.setProperty("width","0","important"),a.style.setProperty("height","0","important"),a.style.setProperty("overflow","visible","important");const n=a.attachShadow({mode:"open"});let o;if("adoptedStyleSheets"in n&&typeof CSSStyleSheet<"u"&&"replaceSync"in CSSStyleSheet.prototype){const r=new CSSStyleSheet;r.replaceSync(le(t,e)),n.adoptedStyleSheets=[r],o=(l,d)=>{r.replaceSync(le(l,d))}}else{const r=document.createElement("style");r.textContent=le(t,e),n.appendChild(r),o=(l,d)=>{r.textContent=le(l,d)}}const s=document.createElement("div");return s.id="dataspeak-widget-app",n.appendChild(s),document.body.appendChild(a),{host:a,shadowRoot:n,mountContainer:s,updateStyles:o}}var V,M,ke,We,ye=Object.is,ce=0,Re=[],ve=[],T=v,Ue=T.__b,Oe=T.__r,Be=T.diffed,Fe=T.__c,Ke=T.unmount,Ge=T.__;function we(t,e){T.__h&&T.__h(M,t,ce||e),ce=0;var a=M.__H||(M.__H={__:[],__h:[]});return t>=a.__.length&&a.__.push({}),a.__[t]}function W(t){return ce=1,ht(Ve,t)}function ht(t,e,a){var n=we(V++,2);if(n.t=t,!n.__c&&(n.__=[Ve(void 0,e),function(s){var r=n.__N?n.__N[0]:n.__[0],l=n.t(r,s);ye(r,l)||(n.__N=[l,n.__[1]],n.__c.setState({}))}],n.__c=M,!M.__f)){M.__f=!0;var o=M.shouldComponentUpdate;M.shouldComponentUpdate=function(s,r,l){var d=this.__H;if(!d)return!0;var _=!1,c=this.props!=s;if(d.__.some(function(h){h.__N&&(_=!0,ye(h.__[0],h.__N[0])||(c=!0))}),o){var g=o.call(this,s,r,l);return _?g||c:g}return!_||c}}return n.__}function R(t,e){var a=we(V++,3);!T.__s&&Je(a.__H,e)&&(a.__P=!0,a.__=t,a.u=e,M.__H.__h.push(a))}function Q(t){return ce=5,bt(function(){return{current:t}},[])}function bt(t,e){var a=we(V++,7);return Je(a.__H,e)&&(a.__=t(),a.__H=e),a.__}function gt(){var t;do{for(;t=ve.shift();)try{X(t)}catch(a){T.__e(a,{__:(t=t.__P)&&t.__v})}for(;t=Re.shift();){var e=t.__H;if(t.__P&&e)try{e.__h.some(X),e.__h.some(Se),e.__h=[]}catch(a){e.__h=[],T.__e(a,t.__v)}}}while(ve.length)}T.__b=function(t){M=null,Ue&&Ue(t)},T.__=function(t,e){t&&e.__k&&e.__k.__m&&(t.__m=e.__k.__m),Ge&&Ge(t,e)},T.__r=function(t){Oe&&Oe(t),V=0;var e=(M=t.__c).__H;e&&(ke==M?M.__h=[]:(e.__h.some(X),e.__h.some(Se),V=0),e.__h=[],e.__.some(function(a){a.__N&&(a.__=a.__N),a.u=a.__N=void 0})),ke=M},T.diffed=function(t){Be&&Be(t);var e=t.__c;e&&e.__H&&(e.__H.__h.length&&qe(Re.push(e)),e.__H.__.some(function(a){a.u&&(a.__H=a.u)})),ke=M=null},T.__c=function(t,e){e.some(function(a){try{a.__h.some(X),a.__h=a.__h.filter(function(n){return!n.__||Se(n)})}catch(n){e.some(function(o){o.__h&&(o.__h=[])}),e=[],T.__e(n,a.__v)}}),Fe&&Fe(t,e)},T.unmount=function(t){Ke&&Ke(t);var e,a,n=t.__c;n&&n.__H&&(n.__H.__.some(function(o){try{if(o.__P&&o.__c){if(a===void 0){for(a=t.__;a&&(!a.__c||!a.__c.__P);)a=a.__;a=a&&a.__c}o.__P=a,qe(ve.push(o))}else X(o)}catch(s){e=s}}),n.__H=void 0,e&&T.__e(e,n.__v))};var Ye=typeof requestAnimationFrame=="function";function mt(t){var e,a=function(){clearTimeout(n),Ye&&cancelAnimationFrame(e),setTimeout(t)},n=setTimeout(a,35);Ye&&(e=requestAnimationFrame(a))}function qe(t){t!=1&&We==T.requestAnimationFrame||((We=T.requestAnimationFrame)||mt)(gt)}function X(t){var e=M,a=t.__c;typeof a=="function"&&(t.__c=void 0,a()),M=e}function Se(t){var e=M;t.__c=t.__(),M=e}function Je(t,e){return!t||t.length!=e.length||e.some(function(a,n){return!ye(a,t[n])})}function Ve(t,e){return typeof e=="function"?e(t):e}function xt(t){try{const e=new URL(t,"https://dummy-base-domain.internal");return e.protocol==="http:"||e.protocol==="https:"}catch{return!1}}function Y(t){const e=[];let a=t,n=0;for(;a.length>0;){const o=a.match(/^\[([^\]]+)\]\(([^)]+)\)/);if(o){const c=o[2].trim();e.push(xt(c)?u("a",{key:`l${n++}`,href:c,target:"_blank",rel:"noopener noreferrer"},o[1]):o[1]),a=a.slice(o[0].length);continue}const s=a.match(/^\[Source:\s*([^\]]+)\]/);if(s){e.push(u("span",{key:`c${n++}`,class:"dataspeak-source-badge"},`📄 ${s[1]}`)),a=a.slice(s[0].length);continue}const r=a.match(/^(\*\*|__)(.+?)\1/);if(r){e.push(u("strong",{key:`b${n++}`},Y(r[2]))),a=a.slice(r[0].length);continue}const l=a.match(/^`([^`]+)`/);if(l){e.push(u("code",{key:`k${n++}`},l[1])),a=a.slice(l[0].length);continue}const d=a.match(/^(\*|_)(.+?)\1/);if(d){e.push(u("em",{key:`e${n++}`},Y(d[2]))),a=a.slice(d[0].length);continue}const _=a.slice(1).search(/(\[|\*\*|__|`|\*|_)/);if(_===-1){e.push(a);break}e.push(a.slice(0,_+1)),a=a.slice(_+1)}return e}function kt({content:t}){if(!t)return u("span",null,"");const e=t.split(`
`),a=[];let n=[],o=[],s=null,r=0;const l=()=>{n.length&&(a.push(u("ul",{key:`ul${r++}`},n)),n=[]),o.length&&(a.push(u("ol",{key:`ol${r++}`},o)),o=[])};for(const d of e){const _=d.trim();if(_.startsWith("```")){s===null?(l(),s=[]):(a.push(u("pre",{key:`pre${r++}`},u("code",null,s.join(`
`)))),s=null);continue}if(s!==null){s.push(d);continue}const c=_.match(/^[-*]\s+(.*)$/);if(c){o.length&&l(),n.push(u("li",{key:`li${r++}`},Y(c[1])));continue}const g=_.match(/^\d+[.)]\s+(.*)$/);if(g){n.length&&l(),o.push(u("li",{key:`li${r++}`},Y(g[1])));continue}if(l(),!_)continue;const h=_.match(/^(#{1,3})\s+(.*)$/);if(h){a.push(u(`h${h[1].length}`,{key:`h${r++}`},Y(h[2])));continue}a.push(u("p",{key:`p${r++}`},Y(d)))}return s!==null&&a.push(u("pre",{key:`pre${r++}`},u("code",null,s.join(`
`)))),l(),u("div",{class:"dataspeak-markdown-body"},a)}const yt=["What can you help with?","Pricing","Talk to support"],vt=t=>t?new Date(t).toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"}):"";function Qe({initialConfig:t}){var D;const[e,a]=W(!1),[n,o]=W(t),[s,r]=W(null),[l,d]=W([]),[_,c]=W(""),[g,h]=W(!1),[b,f]=W(null),[i,w]=W(null),k=Q(null),S=Q(null),m=Q(null),x=Q(null),$=Q(!1),z=()=>n.greetingMessage||"Hello! How can I help you today?";R(()=>{o(t)},[t]),R(()=>()=>{var p;return(p=x.current)==null?void 0:p.abort()},[]),R(()=>{const p=it(n.publicKey);p&&r(p),d(y=>y.length<=1&&(y.length===0||y[0].id==="msg-greeting")?[{id:"msg-greeting",role:"assistant",text:z(),time:Date.now()}]:y)},[n.publicKey,n.greetingMessage]),R(()=>{var p;(p=k.current)==null||p.scrollIntoView({behavior:"smooth",block:"end"})},[l,g]),R(()=>{var p;if(!$.current){$.current=!0;return}e?setTimeout(()=>{var y;return(y=S.current)==null?void 0:y.focus()},200):(p=m.current)==null||p.focus()},[e]),R(()=>{const p=y=>{y.key==="Escape"&&e&&a(!1)};return window.addEventListener("keydown",p),()=>window.removeEventListener("keydown",p)},[e]),R(()=>{if(i===null||i<=0)return;const p=setTimeout(()=>w(y=>y&&y>1?y-1:null),1e3);return()=>clearTimeout(p)},[i]),R(()=>{const p=S.current;p&&(p.style.height="auto",p.style.height=Math.min(p.scrollHeight,110)+"px")},[_]);const B=()=>{var p;(p=x.current)==null||p.abort(),x.current=null,h(!1),d(y=>y.map((E,K)=>K===y.length-1&&E.role==="assistant"?{...E,isStreaming:!1,text:E.text?E.text+`

*(Generation stopped)*`:"*(Generation cancelled)*"}:E))},pe=()=>{var p;(p=x.current)==null||p.abort(),x.current=null,h(!1),ct(n.publicKey),r(null),d([{id:`msg-greeting-${Date.now()}`,role:"assistant",text:z(),time:Date.now()}]),f(null)},U=async p=>{const y=(p??_).trim();if(!y||g||i!==null)return;c(""),f(null);const E=`user-${Date.now()}`,K=`asst-${Date.now()}`,Xe=Date.now();d(P=>[...P,{id:E,role:"user",text:y,time:Xe},{id:K,role:"assistant",text:"",time:Xe,isStreaming:!0}]),h(!0);const $e=new AbortController;x.current=$e;try{let P=s;(!P||Date.now()>P.expiresAt-6e4)&&(P=await dt(n.apiBase,n.publicKey,P==null?void 0:P.conversationId),r(P)),await ut(n.apiBase,P.sessionToken,y,P.conversationId,G=>d(N=>N.map(C=>C.id===K?{...C,text:C.text+G}:C)),G=>{x.current=null,h(!1),d(N=>N.map(C=>C.id===K?{...C,isStreaming:!1,sources:G.sources}:C))},(G,N)=>{x.current=null,h(!1),f(G),N&&w(N),d(C=>C.filter(Ze=>!(Ze.id===K&&!Ze.text)))},$e.signal)}catch(P){x.current=null,h(!1),P.name!=="AbortError"&&!$e.signal.aborted&&f(P.message||"Unable to establish secure connection"),d(G=>G.filter(N=>!(N.id===K&&!N.text)))}},F=p=>{p.key==="Enter"&&!p.shiftKey&&(p.preventDefault(),U())},q=l.length===1&&!g,H=((D=l[l.length-1])==null?void 0:D.text)==="",A=(p,y="18",E="2")=>u("svg",{width:y,height:y,viewBox:"0 0 24 24",fill:"none",stroke:"currentColor","stroke-width":E,"stroke-linecap":"round","stroke-linejoin":"round"},u("path",{d:p}));return u("div",{class:"dataspeak-container"},[u("button",{ref:m,class:`dataspeak-launcher ${e?"is-open":""}`,onClick:()=>{a(!e),f(null)},"aria-label":e?"Close chat assistant":"Open chat assistant","aria-expanded":e},A(e?"M18 6L6 18M6 6l12 12":"M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z","26")),u("div",{class:`dataspeak-panel ${e?"open":""}`,role:"dialog","aria-modal":e?"true":"false","aria-label":n.widgetTitle||"AI Assistant","aria-hidden":e?"false":"true"},[u("div",{class:"dataspeak-header"},[u("div",{class:"dataspeak-header-left"},[u("div",{class:"dataspeak-avatar"},"AI"),u("div",null,[u("div",{class:"dataspeak-header-title"},n.widgetTitle||"AI Assistant"),u("div",{class:"dataspeak-header-status"},[u("span",{class:"dataspeak-status-dot"}),"Online"])])]),u("div",{class:"dataspeak-header-actions"},[u("button",{class:"dataspeak-icon-btn",onClick:pe,title:"Start new chat","aria-label":"Start new chat"},A("M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8M21 3v5h-5M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16M3 21v-5h5")),u("button",{class:"dataspeak-icon-btn",onClick:()=>a(!1),title:"Close chat","aria-label":"Close chat"},A("M18 6L6 18M6 6l12 12"))])]),u("div",{class:"dataspeak-messages","aria-live":"polite"},[...l.map(p=>p.role==="assistant"&&p.text===""&&p.isStreaming?null:u("div",{key:p.id,class:`dataspeak-msg-row ${p.role}`},[u("div",{class:"dataspeak-bubble"},p.role==="assistant"?u(kt,{content:p.text}):p.text),p.sources&&p.sources.length>0?u("div",{class:"dataspeak-sources"},p.sources.map((y,E)=>u("span",{key:`s${E}`,class:"dataspeak-source-badge"},`📄 ${y.document_name}${y.page_number?` (p. ${y.page_number})`:""}`))):null,!p.isStreaming&&p.time?u("div",{class:"dataspeak-time"},vt(p.time)):null])),g&&H?u("div",{class:"dataspeak-typing","aria-label":"Assistant is thinking"},[u("span",{class:"dataspeak-dot"}),u("span",{class:"dataspeak-dot"}),u("span",{class:"dataspeak-dot"})]):null,q?u("div",{class:"dataspeak-chips"},yt.map(p=>u("button",{key:p,class:"dataspeak-chip",onClick:()=>U(p)},p))):null,u("div",{ref:k})]),b?u("div",{class:"dataspeak-error-banner",role:"alert"},[u("span",null,b),i!==null?u("span",{class:"dataspeak-countdown"},` (${i}s)`):null]):null,u("div",{class:"dataspeak-footer"},[u("div",{class:"dataspeak-input-row"},[u("textarea",{ref:S,class:"dataspeak-input",placeholder:i!==null?`Rate limit active... wait ${i}s`:"Type a message...",value:_,disabled:i!==null,rows:1,onInput:p=>c(p.target.value),onKeyDown:F}),g?u("button",{class:"dataspeak-stop-btn",onClick:B,"aria-label":"Stop generation",title:"Stop generation"},u("svg",{width:"14",height:"14",viewBox:"0 0 24 24",fill:"currentColor"},u("rect",{x:"4",y:"4",width:"16",height:"16",rx:"2"}))):u("button",{class:"dataspeak-send-btn",onClick:()=>U(),disabled:!_.trim()||i!==null,"aria-label":"Send message"},A("M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z","16","2.5"))]),u("div",{class:"dataspeak-branding"},["Powered by ",u("a",{href:"https://dataspeak.ai",target:"_blank",rel:"noopener noreferrer"},"DataSpeakAI")])])])])}const I=document.currentScript||null;function wt(){let t="",e=window.location.origin,a="#3b82f6",n="AI Assistant",o="Hello! How can I help you today?",s="bottom-right",r=1,l=!1,d=!1,_=!1,c=!1,g=!1;if(I){t=I.getAttribute("data-key")||"";const h=I.src;if(h)try{e=new URL(h).origin}catch{}const b=I.getAttribute("data-api");b&&(e=b),I.getAttribute("data-theme")&&(a=I.getAttribute("data-theme"),d=!0),I.getAttribute("data-title")&&(n=I.getAttribute("data-title"),_=!0),I.getAttribute("data-position")&&(s=I.getAttribute("data-position"),g=!0),I.getAttribute("data-welcome")&&(o=I.getAttribute("data-welcome"),c=!0)}return{config:{publicKey:t,apiBase:e,themeColor:a,widgetTitle:n,greetingMessage:o,position:s,welcomeDelay:r,soundEnabled:l},hasExplicitTheme:d,hasExplicitTitle:_,hasExplicitGreeting:c,hasExplicitPosition:g}}function de(t){const{config:e,hasExplicitTheme:a,hasExplicitTitle:n,hasExplicitGreeting:o,hasExplicitPosition:s}=wt(),r={...e,...t};if(!r.publicKey){console.warn("[DataSpeakAI] Missing data-key on widget script. Widget initialization aborted.");return}if(document.getElementById("dataspeak-chatbot-widget-root"))return;const l=ft(r.themeColor,r.position);return je(u(Qe,{initialConfig:r}),l.mountContainer),pt(r.apiBase,r.publicKey).then(d=>{const _=(t==null?void 0:t.themeColor)||(a?r.themeColor:d.themeColor||r.themeColor||"#3b82f6"),c=(t==null?void 0:t.position)||(s?r.position:d.position||r.position||"bottom-right"),g=(t==null?void 0:t.widgetTitle)||(n?r.widgetTitle:d.widgetTitle||r.widgetTitle||"AI Assistant"),h=(t==null?void 0:t.greetingMessage)||(o?r.greetingMessage:d.greetingMessage||r.greetingMessage||"Hello! How can I help you today?"),b=(t==null?void 0:t.soundEnabled)??d.soundEnabled??r.soundEnabled,f=(t==null?void 0:t.welcomeDelay)??d.welcomeDelay??r.welcomeDelay;l.updateStyles(_,c);const i={...r,themeColor:_,position:c,widgetTitle:g,greetingMessage:h,soundEnabled:b,welcomeDelay:f};je(u(Qe,{initialConfig:i}),l.mountContainer)}).catch(()=>{}),l}return typeof window<"u"&&(document.readyState==="loading"?document.addEventListener("DOMContentLoaded",()=>de()):de(),window.DataSpeakAI={init:de,version:"1.0.0"}),_e.initWidget=de,Object.defineProperty(_e,Symbol.toStringTag,{value:"Module"}),_e})({});
