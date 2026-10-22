var DataSpeakAIWidget=(function(_e){"use strict";var v,$e,N,Ce,G,Ae,Y,Me,de,pe,Q={},X=[],Xe=/^m(i|n|o|s|text|space)$/,ue=Array.isArray,fe=X.slice,L=Object.assign;function Z(t){t&&t.parentNode&&t.remove()}function d(t,e,n){var a,r,o,i={},l=arguments.length;for(o in e)o=="key"?a=e[o]:o=="ref"&&typeof t!="function"?r=e[o]:i[o]=e[o];return l>2&&(i.children=l>3?fe.call(arguments,2):n),K(t,i,a,r,null)}function K(t,e,n,a,r){var o={type:t,props:e,key:n,ref:a,__k:null,__:null,__b:0,__e:null,__c:null,constructor:void 0,__v:r||++$e,__i:-1,__u:0};return!r&&v.vnode&&v.vnode(o),o}function ee(t){return t.children}function te(t,e){this.props=t,this.context=e,this.__g=0}function j(t,e){if(e==null)return t.__?j(t.__,t.__i+1):null;for(var n;e<t.__k.length;e++)if((n=t.__k[e])&&n.__e)return n.__e;return typeof t.type!="function"||t.props.__P?null:j(t)}function Ie(t){if((t=t.__)&&t.__c&&!t.props.__P)return t.__e=null,t.__k.some(function(e){return e&&(t.__e=e.__e)}),Ie(t)}function Pe(t){(8&t.__g||!(t.__g|=8)||!N.push(t)||G++)&&Ce==v.debounceRendering||((Ce=v.debounceRendering)||queueMicrotask)(Ze)}function Ze(){var t,e,n,a,r,o,i,l,_;try{for(e=1;N.length;)N.length>e&&N.sort(Ae),t=N.shift(),e=N.length,8&t.__g&&(a=void 0,r=void 0,o=(r=(n=t).__v).__e,i=[],l=[],(_=n.__P)&&((a=L({constructor:void 0},r)).__v=r.__v+1,v.vnode&&v.vnode(a),he(_,a,r,n.__n,_.namespaceURI,32&r.__u?[o]:null,i,o||j(r),32&r.__u,l),a.__v=r.__v,a.__.__k[a.__i]=a,Ne(i,a,l),r.__=r.__e=null,a.__e!=o&&Ie(a)))}finally{N.length=G=0}}function Te(t,e,n,a,r,o,i,l,_,p,c){var y,h,g,u,s,w,k=a.__k||X,$=e.length;for(_=et(n,e,k,_,$),y=0;y<$;y++)(g=n.__k[y])!=null&&(h=~g.__i&&k[g.__i]||Q,g.__i=y,w=he(t,g,h,r,o,i,l,_,p,c),u=g.__e,(h.ref!=g.ref||8&h.__u)&&(h.ref&&ge(h.ref,null,g,h),g.ref&&c.push(g.ref,g.__c||u,g)),s=s||u,4&g.__u?(_=De(g,_,t,!h.__v),h.__e&&(h.__e=null)):typeof g.type=="function"&&w!==void 0?_=w:u&&(_=u.nextSibling),g.__u&=-7);return n.__e=s,_}function et(t,e,n,a,r){var o,i,l,_,p,c,y,h,g,u,s=n.length,w=s,k=0,$=!1,m=t.__k=Array(r);for(o=0;o<r;o++)(i=e[o])!=null&&typeof i!="boolean"&&typeof i!="function"?(typeof i!="object"||i.constructor==String?i=m[o]=K(null,i):ue(i)?i=m[o]=K(ee,{children:i}):i.constructor===void 0&&i.__b?i=m[o]=K(i.type,i.props,i.key,i.ref,i.__v):m[o]=i,_=o+k,i.__=t,i.__b=t.__b+1,l=null,~(p=i.__i=tt(i,n,_,w))&&(w--,(l=n[p])&&(l.__u|=2)),l&&l.__v?(i.__u|=2,p==_-1?k--:p==_+1?k++:p!=_&&(p>_?k--:k++,$=!0)):(~p||(r>s?k--:r<s&&k++),typeof i.type!="function"&&(i.__u|=4))):m[o]=null;if($){for(c=[],y=[],o=0;o<r;o++)if((i=m[o])&&2&i.__u){for(h=0,g=c.length;h<g;)c[u=h+g>>1]<i.__i?h=u+1:g=u;c[h]=i.__i,y[o]=h+1}for(k=c.length;o--;)y[o]&&(y[o]==k?k--:m[o].__u|=4)}if(w)for(o=0;o<s;o++)!(l=n[o])||2&l.__u||(l.__e==a&&(a=j(l)),be(l,l));return a}function De(t,e,n,a){var r,o,i;if(typeof t.type=="function"){if(t.props.__P)return e;if(r=t.__k)for(o=0;o<r.length;o++)r[o]&&(r[o].__=t,e=De(r[o],e,n,!1));return e}for(e&&!e.parentNode&&(e=j(t))&&!e.parentNode&&(e=null),i=e;i&&i.nodeType==8;)i=i.nextSibling;for(t.__e!=i&&(!a&&n.moveBefore&&t.__e.parentNode?n.moveBefore(t.__e,e):n.insertBefore(t.__e,e||null)),e=t.__e;(e=e&&e.nextSibling)&&e.nodeType==8;);return e}function tt(t,e,n,a){var r,o,i,l=t.key,_=t.type,p=e[n],c=p&&!(2&p.__u);if(p===null&&l==null||c&&l==p.key&&_==p.type)return n;if(a>(c?1:0)){for(r=n-1,o=n+1;r>=0||o<e.length;)if((p=e[i=r>=0?r--:o++])&&!(2&p.__u)&&l==p.key&&_==p.type)return i}return-1}function ze(t,e,n){n==null&&(n=""),e[0]=="-"?t.setProperty(e,n):t[e]=n}function ne(t,e,n,a,r){var o,i;e:if(e=="style")if(typeof n=="string")t.style.cssText=n;else{if(typeof a=="string"&&(t.style.cssText=a=""),a)for(e in a)n&&e in n||ze(t.style,e,"");if(n)for(e in n)a&&n[e]==a[e]||ze(t.style,e,n[e])}else if(e[0]=="o"&&e[1]=="n")(t.__e||(t.__e={}))[e]=n,n&&a||(i=pe[e]||(pe[e]=nt(e)),(t.__a||(t.__a={}))[e]=de,o=e!=(e=e.replace(Me,"$1")),(e=e.slice(2))[0]<"a"&&(e=e.toLowerCase()),n?t.addEventListener(e,i,o):t.removeEventListener(e,i,o));else{if(r=="http://www.w3.org/2000/svg")e=e.replace(/xlink(H|:h)/,"h").replace(/sName$/,"s");else if(e!="width"&&e!="height"&&e!="href"&&e!="list"&&e!="form"&&e!="tabIndex"&&e!="download"&&e!="rowSpan"&&e!="colSpan"&&e!="role"&&e!="popover"&&e in t)try{t[e]=n??"";break e}catch{}typeof n=="function"||(n==null||n===!1&&e[4]!="-"?t.removeAttribute(e):t.setAttribute(e,e=="popover"&&n==1?"":n))}}function nt(t){return function(e){if(this.__e){var n=this.__e[t];if(e[Y]==null)e[Y]=de++;else if(e[Y]<this.__a[t])return;return n(v.event?v.event(e):e)}}}function he(t,e,n,a,r,o,i,l,_,p){var c,y,h,g,u,s,w,k,$,m,x,C,I,U,ce,O,E,F,D,f,b=e.type;if(e.constructor!==void 0)return null;if(128&n.__u&&(_=32&n.__u,c=n.__c.__z)){if(e.__u|=_,y=o=[],c.nodeType==8)for(h=1,g=c.nextSibling;g;g=g.nextSibling){if(g.nodeType==8){if(g.data.startsWith("$s"))h++;else if(g.data.startsWith("/$s")&&!--h)break}o.push(g)}else o.push(c);l=o[0]}(c=v.__b)&&c(e);e:if(typeof b=="function"){u=i.length;try{if(m=e.props,x=(c=b.prototype)&&c.render,C=(c=b.contextType)&&a[c.__c],I=c?C?C.props.value:c.__:a,n.__c?2&(s=e.__c=n.__c).__g&&(s.__g|=1):(x?e.__c=s=new b(m,I):(e.__c=s=new te(m,I),s.constructor=b,s.render=ot),C&&C.sub(s),s.state||(s.state={}),s.__n=a,s.__g|=8,s.__h=[],s.__k=[]),x&&(s.__s||(s.__s=s.state),b.getDerivedStateFromProps&&(s.__s==s.state&&(s.__s=L({},s.__s)),L(s.__s,b.getDerivedStateFromProps(m,s.__s)))),w=s.props,k=s.state,s.__v=e,n.__c){if(x&&!b.getDerivedStateFromProps&&m!==w&&s.componentWillReceiveProps&&s.componentWillReceiveProps(m,I),e.__v==n.__v&&!(8&s.__g)||!(4&s.__g)&&s.shouldComponentUpdate&&s.shouldComponentUpdate(m,s.__s,I)===!1){e.__v!=n.__v&&(s.props=m,s.state=s.__s,s.__g&=-9),e.__e=n.__e,e.__k=n.__k,e.__k.some(function(S){S&&(S.__=e)}),X.push.apply(s.__h,s.__k),s.__k=[],s.__h.length&&i.push(s),l=j(n);break e}s.componentWillUpdate&&s.componentWillUpdate(m,s.__s,I),x&&s.componentDidUpdate&&s.__h.push(function(){s.componentDidUpdate(w,k,$)})}else x&&!b.getDerivedStateFromProps&&s.componentWillMount&&s.componentWillMount(),x&&s.componentDidMount&&s.__h.push(s.componentDidMount);if(s.context=I,s.props=m,s.__P=t,s.__g&=-5,U=v.__r,ce=0,x)s.state=s.__s,s.__g&=-9,U&&U(e),c=s.render(s.props,s.state,s.context),X.push.apply(s.__h,s.__k),s.__k=[];else do s.__g&=-9,U&&U(e),c=s.render(s.props,s.state,s.context),s.state=s.__s;while(8&s.__g&&++ce<25);s.state=s.__s,s.getChildContext&&(a=L({},a,s.getChildContext())),x&&n.__c&&s.getSnapshotBeforeUpdate&&($=s.getSnapshotBeforeUpdate(w,k)),O=c&&c.type===ee&&c.key==null?c.props.children:c,m.__P&&(c=l,r=(t=m.__P).namespaceURI,_=o=null,n.props&&n.props.__P!=t&&(n.__k.some(function(S){S&&be(S,S)}),n.__k=null),l=n.__k?j(n,0):null),l=Te(t,ue(O)?O:[O],e,n,a,r,o,i,l,_,p),m.__P&&(e.__e=null,l=c),e.__u&=-161,128&n.__u&&(s.__z=null),y&&y.some(Z),s.__h.length&&i.push(s),1&s.__g&&(s.__g&=-4)}catch(S){if(i.length=u,e.__v=null,_||o)if(S.then){if(E=0,e.__u|=_?160:128,o){for(~(D=o.indexOf(l||void 0))||(D=o.length);(f=o[D-1])&&f.nodeType==8;)D--;for(;D<o.length;D++)if(f=o[D]){if(o[D]=null,f.nodeType==8){if(f.data.startsWith("$s"))E++||(F=f);else if(E&&f.data.startsWith("/$s")&&!--E){l=f;break}}else if(!E)break}}if(!F){for(;l&&l.nodeType==8&&l.nextSibling;)l=l.nextSibling;F=l}e.__c.__z||(e.__c.__z=F),e.__e=l}else o&&o.some(Z);else e.__e=n.__e;e.__k||(e.__k=n.__k||[]),S.then||He(e),v.__e(S,e,n)}}else l=e.__e=at(n.__e,e,n,a,r,o,i,_,p,t);return(c=v.diffed)&&c(e),128&e.__u?void 0:l}function He(t){t&&(t.__c&&(t.__c.__g|=4),t.__k&&t.__k.some(He))}function Ne(t,e,n){for(var a=0;a<n.length;)ge(n[a++],n[a++],n[a++]);v.__c&&v.__c(e,t),t.some(function(r){try{t=r.__h,r.__h=[],t.some(function(o){o.call(r)})}catch(o){v.__e(o,r.__v)}})}function at(t,e,n,a,r,o,i,l,_,p){var c,y,h,g,u,s,w,k,$,m=n.props||Q,x=e.props,C=e.type;if(C=="svg"?r="http://www.w3.org/2000/svg":C=="math"?r="http://www.w3.org/1998/Math/MathML":r||(r="http://www.w3.org/1999/xhtml"),o){for(c=0;c<o.length;c++)if((u=o[c])&&(C?u.localName==C:u.nodeType==3)){t=u,o[c]=null;break}}if(!t){if(k=p.ownerDocument||document,!C)return k.createTextNode(x);t=k.createElementNS(r,C,x.is&&x),l&&(v.__m&&v.__m(e,o),l=!1),o=null}if(C){if(p=C=="template"?t.content:t,o=C=="textarea"&&x.defaultValue!=null?null:o&&fe.call(p.childNodes),!l&&o)for(m={},c=0;c<t.attributes.length;c++)m[(u=t.attributes[c]).name]=u.value;for(c in m)u=m[c],c=="dangerouslySetInnerHTML"?h=u:c=="children"||c in x||c=="value"&&"defaultValue"in x||c=="checked"&&"defaultChecked"in x||ne(t,c,null,u,r);for(c in $=1&n.__u,x)u=x[c],c=="children"?g=u:c=="dangerouslySetInnerHTML"?y=u:c=="value"?s=u:c=="checked"?w=u:l&&typeof u!="function"||!(m[c]!==u||$&&u!=null)||ne(t,c,u,m[c],r);y?(l||h&&(y.__html==h.__html||y.__html==t.innerHTML)||(t.innerHTML=y.__html),e.__k=[]):(h&&(t.textContent=""),(C=="foreignObject"||r=="http://www.w3.org/1998/Math/MathML"&&Xe.test(C))&&(r="http://www.w3.org/1999/xhtml"),Te(p,ue(g)?g:[g],e,n,a,r,o,i,o?o[0]:n.__k&&j(n,0),l,_),o&&o.some(Z)),l&&C!="textarea"||(c="value",C=="progress"&&s==null?t.removeAttribute(c):s==null||s===t[c]&&(C!="progress"||s)||ne(t,c,s,m[c],r),c="checked",w!=null&&w!=t[c]&&ne(t,c,w,m[c],r))}else m===x||l&&t.data==x||(t.data=x);return t}function ge(t,e,n,a){try{typeof t=="function"?e?e.__x=t(e)||1:a&&(a=a.__c||a.__e)&&(e=a.__x)&&(a.__x=null,typeof e=="function"?e():t(null)):t.current=e}catch(r){v.__e(r,n)}}function be(t,e,n){var a,r;if(v.unmount&&v.unmount(t),!(a=t.ref)||a.current&&a.current!=t.__e||ge(a,null,e,t),a=t.__c){if(a.componentWillUnmount)try{a.componentWillUnmount()}catch(o){v.__e(o,e)}a.__P=a.__n=null}if(a=t.__k)for(r=0;r<a.length;r++)a[r]&&be(a[r],e,typeof t.type!="function"||n&&!t.props.__P);(a=t.__e)&&(n||Z(a),a.__e&&(a.__e=null)),t.__e=t.__c=t.__=null}function ot(t,e,n){return this.constructor(t,n)}function rt(t,e){var n,a,r,o;v.__&&v.__(t,e),e.nodeType==9&&(e=e.documentElement),a=(n=t&&32&t.__u)?null:e.__k,e.__k=K(ee,{children:[t]}),r=[],o=[],he(e,e.__k,a||Q,Q,e.namespaceURI,a?null:e.firstChild?fe.call(e.childNodes):null,r,a?a.__e:e.firstChild,n,o),Ne(r,e.__k,o),e.__k.props.children=null}v={__e:function(t,e,n,a){for(var r,o,i;e=e.__;)if((r=e.__c)&&!(1&r.__g)){r.__g|=4;try{if((o=r.constructor)&&o.getDerivedStateFromError&&(r.setState(o.getDerivedStateFromError(t)),i=8&r.__g),r.componentDidCatch&&(r.componentDidCatch(t,a||{}),i=8&r.__g),i)return void(r.__g|=2)}catch(l){t=l,i=0}}throw G=0,t}},$e=0,te.prototype.setState=function(t,e){var n=this.__s;n&&n!=this.state||(n=this.__s=L({},this.state)),typeof t=="function"&&(t=t(L({},n),this.props)),t&&(L(n,t),this.__v&&(e&&this.__k.push(e),Pe(this)))},te.prototype.forceUpdate=function(t){this.__v&&(this.__g|=4,t&&this.__h.push(t),Pe(this))},te.prototype.render=ee,N=[],G=0,Ae=function(t,e){return t.__v.__b-e.__v.__b},Y=Symbol(),Me=/(PointerCapture)$|Capture$/i,de=0,pe={};const ae="dataspeak_widget_";function je(t){try{const e=localStorage.getItem(`${ae}${t}`);if(!e)return null;const n=JSON.parse(e);return Date.now()>n.expiresAt-6e4?(localStorage.removeItem(`${ae}${t}`),null):n}catch{return null}}function st(t,e){try{localStorage.setItem(`${ae}${t}`,JSON.stringify(e))}catch{}}function it(t){try{localStorage.removeItem(`${ae}${t}`)}catch{}}function Ee(t,e=6e5){return Date.now()>t.expiresAt-e}async function me(t,e,n,a){const r=`${t.replace(/\/+$/,"")}/api/widget/session`,o=await fetch(r,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({public_key:e,conversation_id:n,continuity_token:a})});if(!o.ok){let _="Failed to initialize session";try{_=(await o.json()).detail||_}catch{}throw new Error(_)}const i=await o.json(),l={sessionToken:i.session_token,expiresAt:Date.now()+i.expires_in*1e3,tenantId:i.tenant_id,conversationId:i.conversation_id,continuityToken:i.continuity_token};return st(e,l),l}async function Re(t,e,n){const a=n||je(e);if(!a)return await me(t,e);if(Ee(a))try{return await me(t,e,a.conversationId,a.continuityToken)}catch(r){return console.warn("[Widget] Proactive session renewal failed, attempting existing session:",r),Date.now()<a.expiresAt-3e4?a:await me(t,e)}return a}async function lt(t,e){try{const n=`${t.replace(/\/+$/,"")}/api/widget/config?key=${encodeURIComponent(e)}`,a=await fetch(n);if(!a.ok)return{};const r=await a.json();return{themeColor:r.theme_color,widgetTitle:r.widget_title,greetingMessage:r.greeting_message,position:r.position,welcomeDelay:r.welcome_delay,soundEnabled:r.sound_enabled}}catch{return{}}}function Le(t){const e=t.trim();if(!e.startsWith("data:"))return null;const n=e.slice(5).trim();if(!n||n==="[DONE]")return null;try{return JSON.parse(n)}catch{return null}}class ct{constructor(){this.buffer=""}feed(e){this.buffer+=e;const n=this.buffer.split(`

`);this.buffer=n.pop()||"";const a=[];for(const r of n){const o=Le(r);o&&a.push(o)}return a}flush(){if(!this.buffer.trim())return[];const e=Le(this.buffer);return this.buffer="",e?[e]:[]}}async function _t(t,e,n,a,r,o,i,l){const _=`${t.replace(/\/+$/,"")}/api/chat/widget`;try{const p=await fetch(_,{method:"POST",signal:l,headers:{"Content-Type":"application/json",Authorization:`Bearer ${e}`,Accept:"text/event-stream"},body:JSON.stringify({query:n,session_token:e,conversation_id:a,stream:!0})});if(p.status===429){const u=p.headers.get("Retry-After"),s=u?parseInt(u,10):5;let w="Too many requests. Please wait before asking again.";try{const k=await p.json();k.detail&&(w=k.detail)}catch{}i(w,s);return}if(!p.ok){let u="Failed to send message";try{const s=await p.json();s.detail&&(u=s.detail)}catch{}i(u);return}if(!p.body){i("No response received from assistant");return}const c=p.body.getReader(),y=new TextDecoder("utf-8"),h=new ct;for(;;){if(l!=null&&l.aborted){try{await c.cancel()}catch{}return}const{done:u,value:s}=await c.read();if(u)break;const w=y.decode(s,{stream:!0}),k=h.feed(w);for(const $ of k){if($.error){i($.error);try{await c.cancel()}catch{}return}$.chunk&&r($.chunk),$.done&&o({conversationId:$.conversation_id||a,messageId:$.message_id,sources:$.sources||[]})}}const g=h.flush();for(const u of g){if(u.error){i(u.error);return}u.chunk&&r(u.chunk),u.done&&o({conversationId:u.conversation_id||a,messageId:u.message_id,sources:u.sources||[]})}}catch(p){if(p.name==="AbortError"||l!=null&&l.aborted)return;i(p.message||"Network connection error")}}function oe(t="#3b82f6",e="bottom-right"){const n=e==="bottom-left",a=n?"bottom: 20px; left: 20px;":"bottom: 20px; right: 20px;";return`
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

.dataspeak-source-badge.unverified {
  background: #fffbeb;
  color: #b45309;
  border: 1px solid #fde68a;
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

.dataspeak-stop-btn {
  width: 36px;
  height: 36px;
  border-radius: 18px;
  background-color: #ef4444;
  color: #ffffff;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background-color 0.15s, transform 0.15s;
}

.dataspeak-stop-btn:hover {
  background-color: #dc2626;
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

.dataspeak-error-banner {
  background-color: #fee2e2;
  color: #991b1b;
  font-size: 12px;
  padding: 6px 12px;
  border-top: 1px solid #fecaca;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.dataspeak-countdown {
  font-weight: 600;
}

.dataspeak-retry-btn {
  background: #ffffff;
  border: 1px solid #f87171;
  color: #b91c1c;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.15s;
}

.dataspeak-retry-btn:hover {
  background: #fef2f2;
}
`}function dt(t="#3b82f6",e="bottom-right"){const n=document.createElement("div");n.id="dataspeak-chatbot-widget-root",n.style.setProperty("display","block","important"),n.style.setProperty("visibility","visible","important"),n.style.setProperty("position","fixed","important"),n.style.setProperty("z-index","2147483647","important"),n.style.setProperty("border","none","important"),n.style.setProperty("margin","0","important"),n.style.setProperty("padding","0","important"),n.style.setProperty("width","0","important"),n.style.setProperty("height","0","important"),n.style.setProperty("overflow","visible","important");const a=n.attachShadow({mode:"open"});let r;if("adoptedStyleSheets"in a&&typeof CSSStyleSheet<"u"&&"replaceSync"in CSSStyleSheet.prototype){const i=new CSSStyleSheet;i.replaceSync(oe(t,e)),a.adoptedStyleSheets=[i],r=(l,_)=>{i.replaceSync(oe(l,_))}}else{const i=document.createElement("style");i.textContent=oe(t,e),a.appendChild(i),r=(l,_)=>{i.textContent=oe(l,_)}}const o=document.createElement("div");return o.id="dataspeak-widget-app",a.appendChild(o),document.body.appendChild(n),{host:n,shadowRoot:a,mountContainer:o,updateStyles:r}}var J,M,ye,We,ke=Object.is,re=0,Ue=[],xe=[],A=v,Be=A.__b,Oe=A.__r,Fe=A.diffed,qe=A.__c,Ke=A.unmount,Je=A.__;function ve(t,e){A.__h&&A.__h(M,t,re||e),re=0;var n=M.__H||(M.__H={__:[],__h:[]});return t>=n.__.length&&n.__.push({}),n.__[t]}function H(t){return re=1,pt(Qe,t)}function pt(t,e,n){var a=ve(J++,2);if(a.t=t,!a.__c&&(a.__=[Qe(void 0,e),function(o){var i=a.__N?a.__N[0]:a.__[0],l=a.t(i,o);ke(i,l)||(a.__N=[l,a.__[1]],a.__c.setState({}))}],a.__c=M,!M.__f)){M.__f=!0;var r=M.shouldComponentUpdate;M.shouldComponentUpdate=function(o,i,l){var _=this.__H;if(!_)return!0;var p=!1,c=this.props!=o;if(_.__.some(function(h){h.__N&&(p=!0,ke(h.__[0],h.__N[0])||(c=!0))}),r){var y=r.call(this,o,i,l);return p?y||c:y}return!p||c}}return a.__}function W(t,e){var n=ve(J++,3);!A.__s&&Ye(n.__H,e)&&(n.__P=!0,n.__=t,n.u=e,M.__H.__h.push(n))}function se(t){return re=5,ut(function(){return{current:t}},[])}function ut(t,e){var n=ve(J++,7);return Ye(n.__H,e)&&(n.__=t(),n.__H=e),n.__}function ft(){var t;do{for(;t=xe.shift();)try{V(t)}catch(n){A.__e(n,{__:(t=t.__P)&&t.__v})}for(;t=Ue.shift();){var e=t.__H;if(t.__P&&e)try{e.__h.some(V),e.__h.some(we),e.__h=[]}catch(n){e.__h=[],A.__e(n,t.__v)}}}while(xe.length)}A.__b=function(t){M=null,Be&&Be(t)},A.__=function(t,e){t&&e.__k&&e.__k.__m&&(t.__m=e.__k.__m),Je&&Je(t,e)},A.__r=function(t){Oe&&Oe(t),J=0;var e=(M=t.__c).__H;e&&(ye==M?M.__h=[]:(e.__h.some(V),e.__h.some(we),J=0),e.__h=[],e.__.some(function(n){n.__N&&(n.__=n.__N),n.u=n.__N=void 0})),ye=M},A.diffed=function(t){Fe&&Fe(t);var e=t.__c;e&&e.__H&&(e.__H.__h.length&&Ge(Ue.push(e)),e.__H.__.some(function(n){n.u&&(n.__H=n.u)})),ye=M=null},A.__c=function(t,e){e.some(function(n){try{n.__h.some(V),n.__h=n.__h.filter(function(a){return!a.__||we(a)})}catch(a){e.some(function(r){r.__h&&(r.__h=[])}),e=[],A.__e(a,n.__v)}}),qe&&qe(t,e)},A.unmount=function(t){Ke&&Ke(t);var e,n,a=t.__c;a&&a.__H&&(a.__H.__.some(function(r){try{if(r.__P&&r.__c){if(n===void 0){for(n=t.__;n&&(!n.__c||!n.__c.__P);)n=n.__;n=n&&n.__c}r.__P=n,Ge(xe.push(r))}else V(r)}catch(o){e=o}}),a.__H=void 0,e&&A.__e(e,a.__v))};var Ve=typeof requestAnimationFrame=="function";function ht(t){var e,n=function(){clearTimeout(a),Ve&&cancelAnimationFrame(e),setTimeout(t)},a=setTimeout(n,35);Ve&&(e=requestAnimationFrame(n))}function Ge(t){t!=1&&We==A.requestAnimationFrame||((We=A.requestAnimationFrame)||ht)(ft)}function V(t){var e=M,n=t.__c;typeof n=="function"&&(t.__c=void 0,n()),M=e}function we(t){var e=M;t.__c=t.__(),M=e}function Ye(t,e){return!t||t.length!=e.length||e.some(function(n,a){return!ke(n,t[a])})}function Qe(t,e){return typeof e=="function"?e(t):e}function gt(t){try{const e=new URL(t,"https://dummy-base-domain.internal");return e.protocol==="http:"||e.protocol==="https:"}catch{return!1}}function ie(t){const e=[];let n=t,a=0;for(;n.length>0;){const r=n.match(/^\[([^\]]+)\]\(([^)]+)\)/);if(r){const c=r[1],y=r[2].trim();gt(y)?e.push(d("a",{key:`lnk-${a++}`,href:y,target:"_blank",rel:"noopener noreferrer"},c)):e.push(c),n=n.slice(r[0].length);continue}const o=n.match(/^(\*\*|__)(.*?)\1/);if(o&&o[2]){e.push(d("strong",{key:`b-${a++}`},ie(o[2]))),n=n.slice(o[0].length);continue}const i=n.match(/^`([^`]+)`/);if(i&&i[1]){e.push(d("code",{key:`code-${a++}`},i[1])),n=n.slice(i[0].length);continue}const l=n.match(/^(\*|_)(.*?)\1/);if(l&&l[2]){e.push(d("em",{key:`em-${a++}`},ie(l[2]))),n=n.slice(l[0].length);continue}const _=n.match(/^\[Source:\s*([^\]]+)\]/);if(_&&_[1]){e.push(d("span",{key:`cit-${a++}`,class:"dataspeak-source-badge"},`📄 ${_[1]}`)),n=n.slice(_[0].length);continue}const p=n.search(/(\[|\*\*|__|`|\*|_)/);if(p===-1){e.push(n);break}else p===0?(e.push(n[0]),n=n.slice(1)):(e.push(n.slice(0,p)),n=n.slice(p))}return e}function bt({content:t}){if(!t)return d("span",null,"");const e=t.split(`
`),n=[];let a=[],r=0;for(let o=0;o<e.length;o++){const i=e[o],l=i.trim(),_=l.match(/^[-*]\s+(.*)$/);if(_){a.push(d("li",{key:`li-${r}-${a.length}`},ie(_[1])));continue}a.length>0&&(n.push(d("ul",{key:`ul-${r++}`},a)),a=[]),l.length!==0&&n.push(d("p",{key:`p-${r++}`},ie(i)))}return a.length>0&&n.push(d("ul",{key:`ul-${r++}`},a)),d("div",{class:"dataspeak-markdown-body"},n)}function mt({initialConfig:t}){var D;const[e,n]=H(!1),[a,r]=H(t),[o,i]=H(null),[l,_]=H([]),[p,c]=H(""),[y,h]=H(!1),[g,u]=H(null),[s,w]=H(null),[k,$]=H(null),m=se(null),x=se(null),C=se(null),I=se(null);W(()=>()=>{var f;(f=I.current)==null||f.abort()},[]),W(()=>{let f=je(a.publicKey);f&&i(f);const b=a.greetingMessage||"Hello! How can I help you today?";_([{id:"msg-greeting",role:"assistant",text:b}])},[a.publicKey]),W(()=>{const b=setInterval(async()=>{if(o&&Ee(o))try{const S=await Re(a.apiBase,a.publicKey,o);i(S)}catch{}},3e5);return()=>clearInterval(b)},[a.apiBase,a.publicKey,o]),W(()=>{m.current&&m.current.scrollIntoView({behavior:"smooth"})},[l,y]),W(()=>{var f;e?setTimeout(()=>{var b;return(b=x.current)==null?void 0:b.focus()},150):(f=C.current)==null||f.focus()},[e]),W(()=>{const f=b=>{b.key==="Escape"&&e&&n(!1)};return window.addEventListener("keydown",f),()=>window.removeEventListener("keydown",f)},[e]),W(()=>{if(s===null||s<=0)return;const f=setTimeout(()=>{w(b=>b&&b>1?b-1:null)},1e3);return()=>clearTimeout(f)},[s]);const U=()=>{n(!e),u(null)},ce=()=>{I.current&&(I.current.abort(),I.current=null),h(!1),_(f=>f.map((b,S)=>S===f.length-1&&b.role==="assistant"?{...b,isStreaming:!1,text:b.text?b.text+`

*(Generation stopped)*`:"*(Generation cancelled)*"}:b))},O=async()=>{I.current&&(I.current.abort(),I.current=null),h(!1),it(a.publicKey),i(null),_([{id:`msg-greeting-${Date.now()}`,role:"assistant",text:a.greetingMessage||"Hello! How can I help you today?"}]),u(null)},E=async()=>{const f=p.trim();if(!f||y||s!==null)return;c(""),u(null),$(f);const b=`user-${Date.now()}`,S=`asst-${Date.now()}`;_(R=>[...R,{id:b,role:"user",text:f},{id:S,role:"assistant",text:"",isStreaming:!0}]),h(!0);const Se=new AbortController;I.current=Se;try{const R=await Re(a.apiBase,a.publicKey,o);i(R),await _t(a.apiBase,R.sessionToken,f,R.conversationId,B=>{_(P=>P.map(z=>z.id===S?{...z,text:z.text+B}:z))},B=>{I.current=null,h(!1),$(null),_(P=>P.map(z=>z.id===S?{...z,isStreaming:!1,sources:B.sources}:z))},(B,P)=>{I.current=null,h(!1),u(B),P&&w(P),_(z=>z.filter(q=>!(q.id===S&&!q.text)).map(q=>q.id===S?{...q,isStreaming:!1}:q))},Se.signal)}catch(R){I.current=null,h(!1),R.name!=="AbortError"&&!Se.signal.aborted&&u(R.message||"Unable to establish secure connection"),_(B=>B.filter(P=>!(P.id===S&&!P.text)).map(P=>P.id===S?{...P,isStreaming:!1}:P))}},F=f=>{f.key==="Enter"&&!f.shiftKey&&(f.preventDefault(),E())};return d("div",{class:"dataspeak-container"},[d("button",{ref:C,class:"dataspeak-launcher",onClick:U,"aria-label":e?"Close chat assistant":"Open chat assistant","aria-expanded":e},e?d("svg",{viewBox:"0 0 24 24",fill:"none",stroke:"currentColor","stroke-width":"2"},d("path",{d:"M18 6L6 18M6 6l12 12"})):d("svg",{viewBox:"0 0 24 24",fill:"none",stroke:"currentColor","stroke-width":"2"},[d("path",{d:"M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"})])),d("div",{class:`dataspeak-panel ${e?"open":""}`,role:"dialog","aria-modal":"true","aria-label":a.widgetTitle||"AI Assistant","aria-hidden":e?"false":"true"},[d("div",{class:"dataspeak-header"},[d("div",{class:"dataspeak-header-left"},[d("div",{class:"dataspeak-avatar"},"AI"),d("div",null,[d("div",{class:"dataspeak-header-title"},a.widgetTitle||"AI Assistant"),d("div",{class:"dataspeak-header-status"},[d("span",{class:"dataspeak-status-dot"}),"Online"])])]),d("div",{class:"dataspeak-header-actions"},[d("button",{class:"dataspeak-icon-btn",onClick:O,title:"Start new chat","aria-label":"Start new chat"},d("svg",{width:"18",height:"18",viewBox:"0 0 24 24",fill:"none",stroke:"currentColor","stroke-width":"2"},d("path",{d:"M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8M21 3v5h-5M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16M3 21v-5h5"}))),d("button",{class:"dataspeak-icon-btn",onClick:()=>n(!1),title:"Close chat","aria-label":"Close chat"},d("svg",{width:"18",height:"18",viewBox:"0 0 24 24",fill:"none",stroke:"currentColor","stroke-width":"2"},d("path",{d:"M18 6L6 18M6 6l12 12"})))])]),d("div",{class:"dataspeak-messages","aria-live":"polite"},[...l.map(f=>d("div",{key:f.id,class:`dataspeak-msg-row ${f.role}`},[d("div",{class:"dataspeak-bubble"},f.role==="assistant"?d(bt,{content:f.text}):f.text),f.sources&&f.sources.length>0?d("div",{class:"dataspeak-sources"},f.sources.map((b,S)=>d("span",{key:`src-${S}`,class:`dataspeak-source-badge ${b.grounding_status==="unverified"?"unverified":""}`,title:b.grounding_status==="unverified"?"Evidence unverified":void 0},`${b.grounding_status==="unverified"?"⚠️":"📄"} ${b.document_name}${b.page_number?` (p. ${b.page_number})`:""}`))):null])),y&&((D=l[l.length-1])==null?void 0:D.text)===""?d("div",{class:"dataspeak-typing","aria-label":"Assistant is thinking"},[d("span",{class:"dataspeak-dot"}),d("span",{class:"dataspeak-dot"}),d("span",{class:"dataspeak-dot"})]):null,d("div",{ref:m})]),g?d("div",{class:"dataspeak-error-banner"},[d("span",null,g),s!==null?d("span",{class:"dataspeak-countdown"},` (${s}s)`):k?d("button",{class:"dataspeak-retry-btn",onClick:()=>{const f=k;u(null),f&&(c(f),setTimeout(()=>{var b;(b=x.current)==null||b.focus()},50))},"aria-label":"Retry previous message"},"Retry"):null]):null,d("div",{class:"dataspeak-footer"},[d("div",{class:"dataspeak-input-row"},[d("textarea",{ref:x,class:"dataspeak-input",placeholder:s!==null?`Rate limit active... wait ${s}s`:"Type a message...",value:p,disabled:s!==null,rows:1,onInput:f=>c(f.target.value),onKeyDown:F}),y?d("button",{class:"dataspeak-stop-btn",onClick:ce,"aria-label":"Stop generation",title:"Stop generation"},d("svg",{width:"14",height:"14",viewBox:"0 0 24 24",fill:"currentColor"},d("rect",{x:"4",y:"4",width:"16",height:"16",rx:"2"}))):d("button",{class:"dataspeak-send-btn",onClick:E,disabled:!p.trim()||s!==null,"aria-label":"Send message"},d("svg",{width:"16",height:"16",viewBox:"0 0 24 24",fill:"none",stroke:"currentColor","stroke-width":"2.5"},d("path",{d:"M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"})))]),d("div",{class:"dataspeak-branding"},["Powered by ",d("a",{href:"https://dataspeak.ai",target:"_blank",rel:"noopener noreferrer"},"DataSpeakAI")])])])])}const T=document.currentScript||null;function yt(){let t="",e=window.location.origin,n="#3b82f6",a="AI Assistant",r="Hello! How can I help you today?",o="bottom-right",i=1,l=!1;if(T){t=T.getAttribute("data-key")||"";const _=T.src;if(_)try{e=new URL(_).origin}catch{}const p=T.getAttribute("data-api");p&&(e=p),T.getAttribute("data-theme")&&(n=T.getAttribute("data-theme")),T.getAttribute("data-title")&&(a=T.getAttribute("data-title")),T.getAttribute("data-position")&&(o=T.getAttribute("data-position")),T.getAttribute("data-welcome")&&(r=T.getAttribute("data-welcome"))}return{publicKey:t,apiBase:e,themeColor:n,widgetTitle:a,greetingMessage:r,position:o,welcomeDelay:i,soundEnabled:l}}function le(t){const n={...yt(),...t};if(!n.publicKey){console.warn("[DataSpeakAI] Missing data-key on widget script. Widget initialization aborted.");return}if(document.getElementById("dataspeak-chatbot-widget-root"))return;const a=dt(n.themeColor,n.position);return rt(d(mt,{initialConfig:n}),a.mountContainer),lt(n.apiBase,n.publicKey).then(r=>{if(r.themeColor||r.position){const o=n.themeColor||r.themeColor||"#3b82f6",i=n.position||r.position||"bottom-right";a.updateStyles(o,i)}}).catch(()=>{}),a}return typeof window<"u"&&(document.readyState==="loading"?document.addEventListener("DOMContentLoaded",()=>le()):le(),window.DataSpeakAI={init:le,version:"1.0.0"}),_e.initWidget=le,Object.defineProperty(_e,Symbol.toStringTag,{value:"Module"}),_e})({});
