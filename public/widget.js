var DataSpeakAIWidget=(function(ae){"use strict";var x,me,N,be,K,ke,q,xe,oe,se,J={},V=[],Oe=/^m(i|n|o|s|text|space)$/,ie=Array.isArray,re=V.slice,E=Object.assign;function G(t){t&&t.parentNode&&t.remove()}function d(t,e,n){var a,s,o,r={},l=arguments.length;for(o in e)o=="key"?a=e[o]:o=="ref"&&typeof t!="function"?s=e[o]:r[o]=e[o];return l>2&&(r.children=l>3?re.call(arguments,2):n),U(t,r,a,s,null)}function U(t,e,n,a,s){var o={type:t,props:e,key:n,ref:a,__k:null,__:null,__b:0,__e:null,__c:null,constructor:void 0,__v:s||++me,__i:-1,__u:0};return!s&&x.vnode&&x.vnode(o),o}function Y(t){return t.children}function X(t,e){this.props=t,this.context=e,this.__g=0}function j(t,e){if(e==null)return t.__?j(t.__,t.__i+1):null;for(var n;e<t.__k.length;e++)if((n=t.__k[e])&&n.__e)return n.__e;return typeof t.type!="function"||t.props.__P?null:j(t)}function ye(t){if((t=t.__)&&t.__c&&!t.props.__P)return t.__e=null,t.__k.some(function(e){return e&&(t.__e=e.__e)}),ye(t)}function ve(t){(8&t.__g||!(t.__g|=8)||!N.push(t)||K++)&&be==x.debounceRendering||((be=x.debounceRendering)||queueMicrotask)(Be)}function Be(){var t,e,n,a,s,o,r,l,c;try{for(e=1;N.length;)N.length>e&&N.sort(ke),t=N.shift(),e=N.length,8&t.__g&&(a=void 0,s=void 0,o=(s=(n=t).__v).__e,r=[],l=[],(c=n.__P)&&((a=E({constructor:void 0},s)).__v=s.__v+1,x.vnode&&x.vnode(a),le(c,a,s,n.__n,c.namespaceURI,32&s.__u?[o]:null,r,o||j(s),32&s.__u,l),a.__v=s.__v,a.__.__k[a.__i]=a,Me(r,a,l),s.__=s.__e=null,a.__e!=o&&ye(a)))}finally{N.length=K=0}}function we(t,e,n,a,s,o,r,l,c,p,_){var g,f,u,h,i,v,k=a.__k||V,M=e.length;for(c=Fe(n,e,k,c,M),g=0;g<M;g++)(u=n.__k[g])!=null&&(f=~u.__i&&k[u.__i]||J,u.__i=g,v=le(t,u,f,s,o,r,l,c,p,_),h=u.__e,(f.ref!=u.ref||8&f.__u)&&(f.ref&&_e(f.ref,null,u,f),u.ref&&_.push(u.ref,u.__c||h,u)),i=i||h,4&u.__u?(c=$e(u,c,t,!f.__v),f.__e&&(f.__e=null)):typeof u.type=="function"&&v!==void 0?c=v:h&&(c=h.nextSibling),u.__u&=-7);return n.__e=i,c}function Fe(t,e,n,a,s){var o,r,l,c,p,_,g,f,u,h,i=n.length,v=i,k=0,M=!1,m=t.__k=Array(s);for(o=0;o<s;o++)(r=e[o])!=null&&typeof r!="boolean"&&typeof r!="function"?(typeof r!="object"||r.constructor==String?r=m[o]=U(null,r):ie(r)?r=m[o]=U(Y,{children:r}):r.constructor===void 0&&r.__b?r=m[o]=U(r.type,r.props,r.key,r.ref,r.__v):m[o]=r,c=o+k,r.__=t,r.__b=t.__b+1,l=null,~(p=r.__i=Ke(r,n,c,v))&&(v--,(l=n[p])&&(l.__u|=2)),l&&l.__v?(r.__u|=2,p==c-1?k--:p==c+1?k++:p!=c&&(p>c?k--:k++,M=!0)):(~p||(s>i?k--:s<i&&k++),typeof r.type!="function"&&(r.__u|=4))):m[o]=null;if(M){for(_=[],g=[],o=0;o<s;o++)if((r=m[o])&&2&r.__u){for(f=0,u=_.length;f<u;)_[h=f+u>>1]<r.__i?f=h+1:u=h;_[f]=r.__i,g[o]=f+1}for(k=_.length;o--;)g[o]&&(g[o]==k?k--:m[o].__u|=4)}if(v)for(o=0;o<i;o++)!(l=n[o])||2&l.__u||(l.__e==a&&(a=j(l)),ce(l,l));return a}function $e(t,e,n,a){var s,o,r;if(typeof t.type=="function"){if(t.props.__P)return e;if(s=t.__k)for(o=0;o<s.length;o++)s[o]&&(s[o].__=t,e=$e(s[o],e,n,!1));return e}for(e&&!e.parentNode&&(e=j(t))&&!e.parentNode&&(e=null),r=e;r&&r.nodeType==8;)r=r.nextSibling;for(t.__e!=r&&(!a&&n.moveBefore&&t.__e.parentNode?n.moveBefore(t.__e,e):n.insertBefore(t.__e,e||null)),e=t.__e;(e=e&&e.nextSibling)&&e.nodeType==8;);return e}function Ke(t,e,n,a){var s,o,r,l=t.key,c=t.type,p=e[n],_=p&&!(2&p.__u);if(p===null&&l==null||_&&l==p.key&&c==p.type)return n;if(a>(_?1:0)){for(s=n-1,o=n+1;s>=0||o<e.length;)if((p=e[r=s>=0?s--:o++])&&!(2&p.__u)&&l==p.key&&c==p.type)return r}return-1}function Se(t,e,n){n==null&&(n=""),e[0]=="-"?t.setProperty(e,n):t[e]=n}function Q(t,e,n,a,s){var o,r;e:if(e=="style")if(typeof n=="string")t.style.cssText=n;else{if(typeof a=="string"&&(t.style.cssText=a=""),a)for(e in a)n&&e in n||Se(t.style,e,"");if(n)for(e in n)a&&n[e]==a[e]||Se(t.style,e,n[e])}else if(e[0]=="o"&&e[1]=="n")(t.__e||(t.__e={}))[e]=n,n&&a||(r=se[e]||(se[e]=qe(e)),(t.__a||(t.__a={}))[e]=oe,o=e!=(e=e.replace(xe,"$1")),(e=e.slice(2))[0]<"a"&&(e=e.toLowerCase()),n?t.addEventListener(e,r,o):t.removeEventListener(e,r,o));else{if(s=="http://www.w3.org/2000/svg")e=e.replace(/xlink(H|:h)/,"h").replace(/sName$/,"s");else if(e!="width"&&e!="height"&&e!="href"&&e!="list"&&e!="form"&&e!="tabIndex"&&e!="download"&&e!="rowSpan"&&e!="colSpan"&&e!="role"&&e!="popover"&&e in t)try{t[e]=n??"";break e}catch{}typeof n=="function"||(n==null||n===!1&&e[4]!="-"?t.removeAttribute(e):t.setAttribute(e,e=="popover"&&n==1?"":n))}}function qe(t){return function(e){if(this.__e){var n=this.__e[t];if(e[q]==null)e[q]=oe++;else if(e[q]<this.__a[t])return;return n(x.event?x.event(e):e)}}}function le(t,e,n,a,s,o,r,l,c,p){var _,g,f,u,h,i,v,k,M,m,y,w,z,W,F,b,$,H,S,D,T=e.type;if(e.constructor!==void 0)return null;if(128&n.__u&&(c=32&n.__u,_=n.__c.__z)){if(e.__u|=c,g=o=[],_.nodeType==8)for(f=1,u=_.nextSibling;u;u=u.nextSibling){if(u.nodeType==8){if(u.data.startsWith("$s"))f++;else if(u.data.startsWith("/$s")&&!--f)break}o.push(u)}else o.push(_);l=o[0]}(_=x.__b)&&_(e);e:if(typeof T=="function"){h=r.length;try{if(m=e.props,y=(_=T.prototype)&&_.render,w=(_=T.contextType)&&a[_.__c],z=_?w?w.props.value:_.__:a,n.__c?2&(i=e.__c=n.__c).__g&&(i.__g|=1):(y?e.__c=i=new T(m,z):(e.__c=i=new X(m,z),i.constructor=T,i.render=Ve),w&&w.sub(i),i.state||(i.state={}),i.__n=a,i.__g|=8,i.__h=[],i.__k=[]),y&&(i.__s||(i.__s=i.state),T.getDerivedStateFromProps&&(i.__s==i.state&&(i.__s=E({},i.__s)),E(i.__s,T.getDerivedStateFromProps(m,i.__s)))),v=i.props,k=i.state,i.__v=e,n.__c){if(y&&!T.getDerivedStateFromProps&&m!==v&&i.componentWillReceiveProps&&i.componentWillReceiveProps(m,z),e.__v==n.__v&&!(8&i.__g)||!(4&i.__g)&&i.shouldComponentUpdate&&i.shouldComponentUpdate(m,i.__s,z)===!1){e.__v!=n.__v&&(i.props=m,i.state=i.__s,i.__g&=-9),e.__e=n.__e,e.__k=n.__k,e.__k.some(function(A){A&&(A.__=e)}),V.push.apply(i.__h,i.__k),i.__k=[],i.__h.length&&r.push(i),l=j(n);break e}i.componentWillUpdate&&i.componentWillUpdate(m,i.__s,z),y&&i.componentDidUpdate&&i.__h.push(function(){i.componentDidUpdate(v,k,M)})}else y&&!T.getDerivedStateFromProps&&i.componentWillMount&&i.componentWillMount(),y&&i.componentDidMount&&i.__h.push(i.componentDidMount);if(i.context=z,i.props=m,i.__P=t,i.__g&=-5,W=x.__r,F=0,y)i.state=i.__s,i.__g&=-9,W&&W(e),_=i.render(i.props,i.state,i.context),V.push.apply(i.__h,i.__k),i.__k=[];else do i.__g&=-9,W&&W(e),_=i.render(i.props,i.state,i.context),i.state=i.__s;while(8&i.__g&&++F<25);i.state=i.__s,i.getChildContext&&(a=E({},a,i.getChildContext())),y&&n.__c&&i.getSnapshotBeforeUpdate&&(M=i.getSnapshotBeforeUpdate(v,k)),b=_&&_.type===Y&&_.key==null?_.props.children:_,m.__P&&(_=l,s=(t=m.__P).namespaceURI,c=o=null,n.props&&n.props.__P!=t&&(n.__k.some(function(A){A&&ce(A,A)}),n.__k=null),l=n.__k?j(n,0):null),l=we(t,ie(b)?b:[b],e,n,a,s,o,r,l,c,p),m.__P&&(e.__e=null,l=_),e.__u&=-161,128&n.__u&&(i.__z=null),g&&g.some(G),i.__h.length&&r.push(i),1&i.__g&&(i.__g&=-4)}catch(A){if(r.length=h,e.__v=null,c||o)if(A.then){if($=0,e.__u|=c?160:128,o){for(~(S=o.indexOf(l||void 0))||(S=o.length);(D=o[S-1])&&D.nodeType==8;)S--;for(;S<o.length;S++)if(D=o[S]){if(o[S]=null,D.nodeType==8){if(D.data.startsWith("$s"))$++||(H=D);else if($&&D.data.startsWith("/$s")&&!--$){l=D;break}}else if(!$)break}}if(!H){for(;l&&l.nodeType==8&&l.nextSibling;)l=l.nextSibling;H=l}e.__c.__z||(e.__c.__z=H),e.__e=l}else o&&o.some(G);else e.__e=n.__e;e.__k||(e.__k=n.__k||[]),A.then||Ce(e),x.__e(A,e,n)}}else l=e.__e=Je(n.__e,e,n,a,s,o,r,c,p,t);return(_=x.diffed)&&_(e),128&e.__u?void 0:l}function Ce(t){t&&(t.__c&&(t.__c.__g|=4),t.__k&&t.__k.some(Ce))}function Me(t,e,n){for(var a=0;a<n.length;)_e(n[a++],n[a++],n[a++]);x.__c&&x.__c(e,t),t.some(function(s){try{t=s.__h,s.__h=[],t.some(function(o){o.call(s)})}catch(o){x.__e(o,s.__v)}})}function Je(t,e,n,a,s,o,r,l,c,p){var _,g,f,u,h,i,v,k,M,m=n.props||J,y=e.props,w=e.type;if(w=="svg"?s="http://www.w3.org/2000/svg":w=="math"?s="http://www.w3.org/1998/Math/MathML":s||(s="http://www.w3.org/1999/xhtml"),o){for(_=0;_<o.length;_++)if((h=o[_])&&(w?h.localName==w:h.nodeType==3)){t=h,o[_]=null;break}}if(!t){if(k=p.ownerDocument||document,!w)return k.createTextNode(y);t=k.createElementNS(s,w,y.is&&y),l&&(x.__m&&x.__m(e,o),l=!1),o=null}if(w){if(p=w=="template"?t.content:t,o=w=="textarea"&&y.defaultValue!=null?null:o&&re.call(p.childNodes),!l&&o)for(m={},_=0;_<t.attributes.length;_++)m[(h=t.attributes[_]).name]=h.value;for(_ in m)h=m[_],_=="dangerouslySetInnerHTML"?f=h:_=="children"||_ in y||_=="value"&&"defaultValue"in y||_=="checked"&&"defaultChecked"in y||Q(t,_,null,h,s);for(_ in M=1&n.__u,y)h=y[_],_=="children"?u=h:_=="dangerouslySetInnerHTML"?g=h:_=="value"?i=h:_=="checked"?v=h:l&&typeof h!="function"||!(m[_]!==h||M&&h!=null)||Q(t,_,h,m[_],s);g?(l||f&&(g.__html==f.__html||g.__html==t.innerHTML)||(t.innerHTML=g.__html),e.__k=[]):(f&&(t.textContent=""),(w=="foreignObject"||s=="http://www.w3.org/1998/Math/MathML"&&Oe.test(w))&&(s="http://www.w3.org/1999/xhtml"),we(p,ie(u)?u:[u],e,n,a,s,o,r,o?o[0]:n.__k&&j(n,0),l,c),o&&o.some(G)),l&&w!="textarea"||(_="value",w=="progress"&&i==null?t.removeAttribute(_):i==null||i===t[_]&&(w!="progress"||i)||Q(t,_,i,m[_],s),_="checked",v!=null&&v!=t[_]&&Q(t,_,v,m[_],s))}else m===y||l&&t.data==y||(t.data=y);return t}function _e(t,e,n,a){try{typeof t=="function"?e?e.__x=t(e)||1:a&&(a=a.__c||a.__e)&&(e=a.__x)&&(a.__x=null,typeof e=="function"?e():t(null)):t.current=e}catch(s){x.__e(s,n)}}function ce(t,e,n){var a,s;if(x.unmount&&x.unmount(t),!(a=t.ref)||a.current&&a.current!=t.__e||_e(a,null,e,t),a=t.__c){if(a.componentWillUnmount)try{a.componentWillUnmount()}catch(o){x.__e(o,e)}a.__P=a.__n=null}if(a=t.__k)for(s=0;s<a.length;s++)a[s]&&ce(a[s],e,typeof t.type!="function"||n&&!t.props.__P);(a=t.__e)&&(n||G(a),a.__e&&(a.__e=null)),t.__e=t.__c=t.__=null}function Ve(t,e,n){return this.constructor(t,n)}function Ge(t,e){var n,a,s,o;x.__&&x.__(t,e),e.nodeType==9&&(e=e.documentElement),a=(n=t&&32&t.__u)?null:e.__k,e.__k=U(Y,{children:[t]}),s=[],o=[],le(e,e.__k,a||J,J,e.namespaceURI,a?null:e.firstChild?re.call(e.childNodes):null,s,a?a.__e:e.firstChild,n,o),Me(s,e.__k,o),e.__k.props.children=null}x={__e:function(t,e,n,a){for(var s,o,r;e=e.__;)if((s=e.__c)&&!(1&s.__g)){s.__g|=4;try{if((o=s.constructor)&&o.getDerivedStateFromError&&(s.setState(o.getDerivedStateFromError(t)),r=8&s.__g),s.componentDidCatch&&(s.componentDidCatch(t,a||{}),r=8&s.__g),r)return void(s.__g|=2)}catch(l){t=l,r=0}}throw K=0,t}},me=0,X.prototype.setState=function(t,e){var n=this.__s;n&&n!=this.state||(n=this.__s=E({},this.state)),typeof t=="function"&&(t=t(E({},n),this.props)),t&&(E(n,t),this.__v&&(e&&this.__k.push(e),ve(this)))},X.prototype.forceUpdate=function(t){this.__v&&(this.__g|=4,t&&this.__h.push(t),ve(this))},X.prototype.render=Y,N=[],K=0,ke=function(t,e){return t.__v.__b-e.__v.__b},q=Symbol(),xe=/(PointerCapture)$|Capture$/i,oe=0,se={};const Z="dataspeak_widget_";function Ye(t){try{const e=localStorage.getItem(`${Z}${t}`);if(!e)return null;const n=JSON.parse(e);return Date.now()>n.expiresAt-6e4?(localStorage.removeItem(`${Z}${t}`),null):n}catch{return null}}function Xe(t,e){try{localStorage.setItem(`${Z}${t}`,JSON.stringify(e))}catch{}}function Qe(t){try{localStorage.removeItem(`${Z}${t}`)}catch{}}async function Ze(t,e,n){const a=`${t.replace(/\/+$/,"")}/api/widget/session`,s=await fetch(a,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({public_key:e,conversation_id:n})});if(!s.ok){let l="Failed to initialize session";try{l=(await s.json()).detail||l}catch{}throw new Error(l)}const o=await s.json(),r={sessionToken:o.session_token,expiresAt:Date.now()+o.expires_in*1e3,tenantId:o.tenant_id,conversationId:o.conversation_id};return Xe(e,r),r}async function et(t,e){try{const n=`${t.replace(/\/+$/,"")}/api/widget/config?key=${encodeURIComponent(e)}`,a=await fetch(n);if(!a.ok)return{};const s=await a.json();return{themeColor:s.theme_color,widgetTitle:s.widget_title,greetingMessage:s.greeting_message,position:s.position,welcomeDelay:s.welcome_delay,soundEnabled:s.sound_enabled}}catch{return{}}}async function tt(t,e,n,a,s,o,r){const l=`${t.replace(/\/+$/,"")}/api/chat/widget`;try{const c=await fetch(l,{method:"POST",headers:{"Content-Type":"application/json",Authorization:`Bearer ${e}`,Accept:"text/event-stream"},body:JSON.stringify({query:n,session_token:e,conversation_id:a,stream:!0})});if(c.status===429){const f=c.headers.get("Retry-After"),u=f?parseInt(f,10):5;let h="Too many requests. Please wait before asking again.";try{const i=await c.json();i.detail&&(h=i.detail)}catch{}r(h,u);return}if(!c.ok){let f="Failed to send message";try{const u=await c.json();u.detail&&(f=u.detail)}catch{}r(f);return}if(!c.body){r("No response received from assistant");return}const p=c.body.getReader(),_=new TextDecoder("utf-8");let g="";for(;;){const{done:f,value:u}=await p.read();if(f)break;g+=_.decode(u,{stream:!0});const h=g.split(`

`);g=h.pop()||"";for(const i of h){const v=i.trim();if(v.startsWith("data:")){const k=v.slice(5).trim();try{const M=JSON.parse(k);M.chunk&&s(M.chunk),M.done&&o({conversationId:M.conversation_id||a,messageId:M.message_id,sources:M.sources||[]})}catch{}}}}}catch(c){r(c.message||"Network connection error")}}function Ae(t="#3b82f6",e="bottom-right"){const n=e==="bottom-left",a=n?"bottom: 20px; left: 20px;":"bottom: 20px; right: 20px;";return`
:host {
  all: initial;
  position: fixed;
  visibility: visible !important;
  z-index: 2147483647;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  font-size: 14px;
  line-height: 1.5;
  letter-spacing: normal;
  text-align: left;
  color: #111827;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.dataspeak-container {
  visibility: visible !important;
}

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

.dataspeak-launcher {
  position: fixed;
  ${a}
  width: 56px;
  height: 56px;
  border-radius: 28px;
  background-color: ${t};
  color: #ffffff;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.2), 0 2px 4px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.2s ease;
  z-index: 2147483647;
  outline: none;
}

.dataspeak-launcher:hover {
  transform: scale(1.06);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.25);
}

.dataspeak-launcher:focus-visible {
  outline: 3px solid #93c5fd;
  outline-offset: 2px;
}

.dataspeak-launcher svg {
  width: 26px;
  height: 26px;
  fill: currentColor;
  transition: transform 0.2s ease;
}

.dataspeak-panel {
  position: fixed;
  ${n?"bottom: 84px; left: 20px;":"bottom: 84px; right: 20px;"}
  width: 380px;
  max-width: calc(100vw - 32px);
  height: 580px;
  max-height: calc(100dvh - 100px);
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 12px 36px rgba(0, 0, 0, 0.16), 0 2px 8px rgba(0, 0, 0, 0.06);
  border: 1px solid rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  z-index: 2147483647;
  opacity: 0;
  visibility: hidden;
  transform: translateY(16px) scale(0.97);
  pointer-events: none;
  transition: opacity 0.22s ease, transform 0.22s cubic-bezier(0.16, 1, 0.3, 1), visibility 0.22s;
}

.dataspeak-panel.open {
  opacity: 1;
  visibility: visible;
  transform: translateY(0) scale(1);
  pointer-events: auto;
}

@media (max-width: 480px) {
  .dataspeak-panel {
    top: 0 !important;
    bottom: 0 !important;
    left: 0 !important;
    right: 0 !important;
    width: 100vw !important;
    height: 100dvh !important;
    max-width: 100vw !important;
    max-height: 100dvh !important;
    border-radius: 0 !important;
    border: none !important;
  }
  .dataspeak-launcher {
    ${a}
  }
}

.dataspeak-header {
  padding: 14px 16px;
  background-color: ${t};
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.dataspeak-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.dataspeak-avatar {
  width: 32px;
  height: 32px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.22);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 14px;
}

.dataspeak-header-title {
  font-weight: 600;
  font-size: 15px;
  line-height: 1.2;
}

.dataspeak-header-status {
  font-size: 11px;
  opacity: 0.88;
  display: flex;
  align-items: center;
  gap: 4px;
}

.dataspeak-status-dot {
  width: 6px;
  height: 6px;
  border-radius: 3px;
  background-color: #34d399;
}

.dataspeak-header-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.dataspeak-icon-btn {
  background: transparent;
  border: none;
  color: #ffffff;
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0.88;
  transition: opacity 0.15s, background-color 0.15s;
}

.dataspeak-icon-btn:hover {
  opacity: 1;
  background-color: rgba(255, 255, 255, 0.18);
}

.dataspeak-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: #f9fafb;
}

.dataspeak-msg-row {
  display: flex;
  flex-direction: column;
  max-width: 85%;
}

.dataspeak-msg-row.user {
  align-self: flex-end;
  align-items: flex-end;
}

.dataspeak-msg-row.assistant {
  align-self: flex-start;
  align-items: flex-start;
}

.dataspeak-bubble {
  padding: 10px 14px;
  font-size: 13.5px;
  line-height: 1.45;
  word-break: break-word;
}

.dataspeak-msg-row.user .dataspeak-bubble {
  background-color: ${t};
  color: #ffffff;
  border-radius: 14px 14px 2px 14px;
}

.dataspeak-msg-row.assistant .dataspeak-bubble {
  background-color: #ffffff;
  color: #1f2937;
  border: 1px solid #e5e7eb;
  border-radius: 14px 14px 14px 2px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

.dataspeak-sources {
  margin-top: 6px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.dataspeak-source-badge {
  font-size: 11px;
  background: #eef2ff;
  color: #4338ca;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 3px;
}

.dataspeak-typing {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 10px 14px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 14px 14px 14px 2px;
  width: fit-content;
}

.dataspeak-dot {
  width: 6px;
  height: 6px;
  border-radius: 3px;
  background-color: #9ca3af;
  animation: dataspeak-bounce 1.4s infinite ease-in-out both;
}

.dataspeak-dot:nth-child(1) { animation-delay: -0.32s; }
.dataspeak-dot:nth-child(2) { animation-delay: -0.16s; }

@keyframes dataspeak-bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

.dataspeak-error-banner {
  margin: 8px 16px;
  padding: 8px 12px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
  border-radius: 8px;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.dataspeak-footer {
  padding: 12px 14px;
  background: #ffffff;
  border-top: 1px solid #e5e7eb;
  flex-shrink: 0;
}

.dataspeak-input-row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}

.dataspeak-input {
  flex: 1;
  border: 1px solid #d1d5db;
  border-radius: 20px;
  padding: 8px 14px;
  font-size: 13.5px;
  line-height: 1.4;
  outline: none;
  resize: none;
  max-height: 96px;
  min-height: 38px;
  color: #111827;
  background: #ffffff;
  font-family: inherit;
  transition: border-color 0.15s;
}

.dataspeak-input:focus {
  border-color: ${t};
}

.dataspeak-send-btn {
  width: 36px;
  height: 36px;
  border-radius: 18px;
  background-color: ${t};
  color: #ffffff;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: opacity 0.15s, transform 0.15s;
}

.dataspeak-send-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  transform: none;
}

.dataspeak-send-btn:not(:disabled):hover {
  transform: scale(1.05);
}

.dataspeak-branding {
  text-align: center;
  font-size: 11px;
  color: #9ca3af;
  margin-top: 6px;
}

.dataspeak-branding a {
  color: #6b7280;
  text-decoration: none;
  font-weight: 500;
}

/* Markdown styling inside assistant bubble */
.dataspeak-bubble p {
  margin-bottom: 6px;
}
.dataspeak-bubble p:last-child {
  margin-bottom: 0;
}
.dataspeak-bubble strong {
  font-weight: 600;
}
.dataspeak-bubble em {
  font-style: italic;
}
.dataspeak-bubble code {
  background: #f3f4f6;
  padding: 2px 4px;
  border-radius: 3px;
  font-family: monospace;
  font-size: 12px;
}
.dataspeak-bubble a {
  color: ${t};
  text-decoration: underline;
  word-break: break-all;
}
.dataspeak-bubble ul, .dataspeak-bubble ol {
  margin-left: 18px;
  margin-bottom: 6px;
}
`}function nt(t="#3b82f6",e="bottom-right"){const n=document.createElement("div");n.id="dataspeak-chatbot-widget-root",n.setAttribute("style","display: block !important; visibility: visible !important; position: fixed !important; z-index: 2147483647 !important; border: none !important; margin: 0 !important; padding: 0 !important; width: 0 !important; height: 0 !important; overflow: visible !important;");const a=n.attachShadow({mode:"open"}),s=document.createElement("style");s.textContent=Ae(t,e),a.appendChild(s);const o=document.createElement("div");return o.id="dataspeak-widget-app",a.appendChild(o),document.body.appendChild(n),{host:n,shadowRoot:a,mountContainer:o,updateStyles:(l,c)=>{s.textContent=Ae(l,c)}}}var R,I,de,Ie,pe=Object.is,ee=0,Te=[],ue=[],C=x,De=C.__b,Pe=C.__r,He=C.diffed,ze=C.__c,Ne=C.unmount,je=C.__;function fe(t,e){C.__h&&C.__h(I,t,ee||e),ee=0;var n=I.__H||(I.__H={__:[],__h:[]});return t>=n.__.length&&n.__.push({}),n.__[t]}function L(t){return ee=1,at(Ue,t)}function at(t,e,n){var a=fe(R++,2);if(a.t=t,!a.__c&&(a.__=[Ue(void 0,e),function(o){var r=a.__N?a.__N[0]:a.__[0],l=a.t(r,o);pe(r,l)||(a.__N=[l,a.__[1]],a.__c.setState({}))}],a.__c=I,!I.__f)){I.__f=!0;var s=I.shouldComponentUpdate;I.shouldComponentUpdate=function(o,r,l){var c=this.__H;if(!c)return!0;var p=!1,_=this.props!=o;if(c.__.some(function(f){f.__N&&(p=!0,pe(f.__[0],f.__N[0])||(_=!0))}),s){var g=s.call(this,o,r,l);return p?g||_:g}return!p||_}}return a.__}function O(t,e){var n=fe(R++,3);!C.__s&&We(n.__H,e)&&(n.__P=!0,n.__=t,n.u=e,I.__H.__h.push(n))}function he(t){return ee=5,ot(function(){return{current:t}},[])}function ot(t,e){var n=fe(R++,7);return We(n.__H,e)&&(n.__=t(),n.__H=e),n.__}function st(){var t;do{for(;t=ue.shift();)try{B(t)}catch(n){C.__e(n,{__:(t=t.__P)&&t.__v})}for(;t=Te.shift();){var e=t.__H;if(t.__P&&e)try{e.__h.some(B),e.__h.some(ge),e.__h=[]}catch(n){e.__h=[],C.__e(n,t.__v)}}}while(ue.length)}C.__b=function(t){I=null,De&&De(t)},C.__=function(t,e){t&&e.__k&&e.__k.__m&&(t.__m=e.__k.__m),je&&je(t,e)},C.__r=function(t){Pe&&Pe(t),R=0;var e=(I=t.__c).__H;e&&(de==I?I.__h=[]:(e.__h.some(B),e.__h.some(ge),R=0),e.__h=[],e.__.some(function(n){n.__N&&(n.__=n.__N),n.u=n.__N=void 0})),de=I},C.diffed=function(t){He&&He(t);var e=t.__c;e&&e.__H&&(e.__H.__h.length&&Ee(Te.push(e)),e.__H.__.some(function(n){n.u&&(n.__H=n.u)})),de=I=null},C.__c=function(t,e){e.some(function(n){try{n.__h.some(B),n.__h=n.__h.filter(function(a){return!a.__||ge(a)})}catch(a){e.some(function(s){s.__h&&(s.__h=[])}),e=[],C.__e(a,n.__v)}}),ze&&ze(t,e)},C.unmount=function(t){Ne&&Ne(t);var e,n,a=t.__c;a&&a.__H&&(a.__H.__.some(function(s){try{if(s.__P&&s.__c){if(n===void 0){for(n=t.__;n&&(!n.__c||!n.__c.__P);)n=n.__;n=n&&n.__c}s.__P=n,Ee(ue.push(s))}else B(s)}catch(o){e=o}}),a.__H=void 0,e&&C.__e(e,a.__v))};var Le=typeof requestAnimationFrame=="function";function it(t){var e,n=function(){clearTimeout(a),Le&&cancelAnimationFrame(e),setTimeout(t)},a=setTimeout(n,35);Le&&(e=requestAnimationFrame(n))}function Ee(t){t!=1&&Ie==C.requestAnimationFrame||((Ie=C.requestAnimationFrame)||it)(st)}function B(t){var e=I,n=t.__c;typeof n=="function"&&(t.__c=void 0,n()),I=e}function ge(t){var e=I;t.__c=t.__(),I=e}function We(t,e){return!t||t.length!=e.length||e.some(function(n,a){return!pe(n,t[a])})}function Ue(t,e){return typeof e=="function"?e(t):e}function rt(t){try{const e=new URL(t,"https://dummy-base-domain.internal");return e.protocol==="http:"||e.protocol==="https:"}catch{return!1}}function te(t){const e=[];let n=t,a=0;for(;n.length>0;){const s=n.match(/^\[([^\]]+)\]\(([^)]+)\)/);if(s){const _=s[1],g=s[2].trim();rt(g)?e.push(d("a",{key:`lnk-${a++}`,href:g,target:"_blank",rel:"noopener noreferrer"},_)):e.push(_),n=n.slice(s[0].length);continue}const o=n.match(/^(\*\*|__)(.*?)\1/);if(o&&o[2]){e.push(d("strong",{key:`b-${a++}`},te(o[2]))),n=n.slice(o[0].length);continue}const r=n.match(/^`([^`]+)`/);if(r&&r[1]){e.push(d("code",{key:`code-${a++}`},r[1])),n=n.slice(r[0].length);continue}const l=n.match(/^(\*|_)(.*?)\1/);if(l&&l[2]){e.push(d("em",{key:`em-${a++}`},te(l[2]))),n=n.slice(l[0].length);continue}const c=n.match(/^\[Source:\s*([^\]]+)\]/);if(c&&c[1]){e.push(d("span",{key:`cit-${a++}`,class:"dataspeak-source-badge"},`📄 ${c[1]}`)),n=n.slice(c[0].length);continue}const p=n.search(/(\[|\*\*|__|`|\*|_)/);if(p===-1){e.push(n);break}else p===0?(e.push(n[0]),n=n.slice(1)):(e.push(n.slice(0,p)),n=n.slice(p))}return e}function lt({content:t}){if(!t)return d("span",null,"");const e=t.split(`
`),n=[];let a=[],s=0;for(let o=0;o<e.length;o++){const r=e[o],l=r.trim(),c=l.match(/^[-*]\s+(.*)$/);if(c){a.push(d("li",{key:`li-${s}-${a.length}`},te(c[1])));continue}a.length>0&&(n.push(d("ul",{key:`ul-${s++}`},a)),a=[]),l.length!==0&&n.push(d("p",{key:`p-${s++}`},te(r)))}return a.length>0&&n.push(d("ul",{key:`ul-${s++}`},a)),d("div",{class:"dataspeak-markdown-body"},n)}function _t({initialConfig:t}){var F;const[e,n]=L(!1),[a,s]=L(t),[o,r]=L(null),[l,c]=L([]),[p,_]=L(""),[g,f]=L(!1),[u,h]=L(null),[i,v]=L(null),k=he(null),M=he(null),m=he(null);O(()=>{let b=Ye(a.publicKey);b&&r(b);const $=a.greetingMessage||"Hello! How can I help you today?";c([{id:"msg-greeting",role:"assistant",text:$}])},[a.publicKey]),O(()=>{k.current&&k.current.scrollIntoView({behavior:"smooth"})},[l,g]),O(()=>{var b;e?setTimeout(()=>{var $;return($=M.current)==null?void 0:$.focus()},150):(b=m.current)==null||b.focus()},[e]),O(()=>{const b=$=>{$.key==="Escape"&&e&&n(!1)};return window.addEventListener("keydown",b),()=>window.removeEventListener("keydown",b)},[e]),O(()=>{if(i===null||i<=0)return;const b=setTimeout(()=>{v($=>$&&$>1?$-1:null)},1e3);return()=>clearTimeout(b)},[i]);const y=()=>{n(!e),h(null)},w=async()=>{Qe(a.publicKey),r(null),c([{id:`msg-greeting-${Date.now()}`,role:"assistant",text:a.greetingMessage||"Hello! How can I help you today?"}]),h(null)},z=async()=>{const b=p.trim();if(!b||g||i!==null)return;_(""),h(null);const $=`user-${Date.now()}`,H=`asst-${Date.now()}`;c(S=>[...S,{id:$,role:"user",text:b},{id:H,role:"assistant",text:"",isStreaming:!0}]),f(!0);try{let S=o;(!S||Date.now()>S.expiresAt-6e4)&&(S=await Ze(a.apiBase,a.publicKey,S==null?void 0:S.conversationId),r(S)),await tt(a.apiBase,S.sessionToken,b,S.conversationId,D=>{c(T=>T.map(A=>A.id===H?{...A,text:A.text+D}:A))},D=>{f(!1),c(T=>T.map(A=>A.id===H?{...A,isStreaming:!1,sources:D.sources}:A))},(D,T)=>{f(!1),h(D),T&&v(T),c(A=>A.filter(Re=>!(Re.id===H&&!Re.text)))})}catch(S){f(!1),h(S.message||"Unable to establish secure connection"),c(D=>D.filter(T=>!(T.id===H&&!T.text)))}},W=b=>{b.key==="Enter"&&!b.shiftKey&&(b.preventDefault(),z())};return d("div",{class:"dataspeak-container"},[d("button",{ref:m,class:"dataspeak-launcher",onClick:y,"aria-label":e?"Close chat assistant":"Open chat assistant","aria-expanded":e},e?d("svg",{viewBox:"0 0 24 24",fill:"none",stroke:"currentColor","stroke-width":"2"},d("path",{d:"M18 6L6 18M6 6l12 12"})):d("svg",{viewBox:"0 0 24 24",fill:"none",stroke:"currentColor","stroke-width":"2"},[d("path",{d:"M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"})])),d("div",{class:`dataspeak-panel ${e?"open":""}`,role:"dialog","aria-modal":"true","aria-label":a.widgetTitle||"AI Assistant","aria-hidden":e?"false":"true"},[d("div",{class:"dataspeak-header"},[d("div",{class:"dataspeak-header-left"},[d("div",{class:"dataspeak-avatar"},"AI"),d("div",null,[d("div",{class:"dataspeak-header-title"},a.widgetTitle||"AI Assistant"),d("div",{class:"dataspeak-header-status"},[d("span",{class:"dataspeak-status-dot"}),"Online"])])]),d("div",{class:"dataspeak-header-actions"},[d("button",{class:"dataspeak-icon-btn",onClick:w,title:"Start new chat","aria-label":"Start new chat"},d("svg",{width:"18",height:"18",viewBox:"0 0 24 24",fill:"none",stroke:"currentColor","stroke-width":"2"},d("path",{d:"M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8M21 3v5h-5M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16M3 21v-5h5"}))),d("button",{class:"dataspeak-icon-btn",onClick:()=>n(!1),title:"Close chat","aria-label":"Close chat"},d("svg",{width:"18",height:"18",viewBox:"0 0 24 24",fill:"none",stroke:"currentColor","stroke-width":"2"},d("path",{d:"M18 6L6 18M6 6l12 12"})))])]),d("div",{class:"dataspeak-messages","aria-live":"polite"},[...l.map(b=>d("div",{key:b.id,class:`dataspeak-msg-row ${b.role}`},[d("div",{class:"dataspeak-bubble"},b.role==="assistant"?d(lt,{content:b.text}):b.text),b.sources&&b.sources.length>0?d("div",{class:"dataspeak-sources"},b.sources.map(($,H)=>d("span",{key:`src-${H}`,class:"dataspeak-source-badge"},`📄 ${$.document_name}${$.page_number?` (p. ${$.page_number})`:""}`))):null])),g&&((F=l[l.length-1])==null?void 0:F.text)===""?d("div",{class:"dataspeak-typing","aria-label":"Assistant is thinking"},[d("span",{class:"dataspeak-dot"}),d("span",{class:"dataspeak-dot"}),d("span",{class:"dataspeak-dot"})]):null,d("div",{ref:k})]),u?d("div",{class:"dataspeak-error-banner"},[d("span",null,u),i!==null?d("span",{style:"font-weight: 600;"},` (${i}s)`):null]):null,d("div",{class:"dataspeak-footer"},[d("div",{class:"dataspeak-input-row"},[d("textarea",{ref:M,class:"dataspeak-input",placeholder:i!==null?`Rate limit active... wait ${i}s`:"Type a message...",value:p,disabled:i!==null,rows:1,onInput:b=>_(b.target.value),onKeyDown:W}),d("button",{class:"dataspeak-send-btn",onClick:z,disabled:!p.trim()||g||i!==null,"aria-label":"Send message"},d("svg",{width:"16",height:"16",viewBox:"0 0 24 24",fill:"none",stroke:"currentColor","stroke-width":"2.5"},d("path",{d:"M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"})))]),d("div",{class:"dataspeak-branding"},["Powered by ",d("a",{href:"https://dataspeak.ai",target:"_blank",rel:"noopener noreferrer"},"DataSpeakAI")])])])])}const P=document.currentScript||null;function ct(){let t="",e=window.location.origin,n="#3b82f6",a="AI Assistant",s="Hello! How can I help you today?",o="bottom-right",r=1,l=!1;if(P){t=P.getAttribute("data-key")||"";const c=P.src;if(c)try{e=new URL(c).origin}catch{}const p=P.getAttribute("data-api");p&&(e=p),P.getAttribute("data-theme")&&(n=P.getAttribute("data-theme")),P.getAttribute("data-title")&&(a=P.getAttribute("data-title")),P.getAttribute("data-position")&&(o=P.getAttribute("data-position")),P.getAttribute("data-welcome")&&(s=P.getAttribute("data-welcome"))}return{publicKey:t,apiBase:e,themeColor:n,widgetTitle:a,greetingMessage:s,position:o,welcomeDelay:r,soundEnabled:l}}function ne(t){const n={...ct(),...t};if(!n.publicKey){console.warn("[DataSpeakAI] Missing data-key on widget script. Widget initialization aborted.");return}if(document.getElementById("dataspeak-chatbot-widget-root"))return;const a=nt(n.themeColor,n.position);return Ge(d(_t,{initialConfig:n}),a.mountContainer),et(n.apiBase,n.publicKey).then(s=>{if(s.themeColor||s.position){const o=n.themeColor||s.themeColor||"#3b82f6",r=n.position||s.position||"bottom-right";a.updateStyles(o,r)}}).catch(()=>{}),a}return typeof window<"u"&&(document.readyState==="loading"?document.addEventListener("DOMContentLoaded",()=>ne()):ne(),window.DataSpeakAI={init:ne,version:"1.0.0"}),ae.initWidget=ne,Object.defineProperty(ae,Symbol.toStringTag,{value:"Module"}),ae})({});
