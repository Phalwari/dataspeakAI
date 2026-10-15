var DataSpeakAIWidget=(function(le){"use strict";var v,xe,N,ve,V,we,G,Se,ce,_e,Y={},X=[],qe=/^m(i|n|o|s|text|space)$/,de=Array.isArray,pe=X.slice,W=Object.assign;function Q(t){t&&t.parentNode&&t.remove()}function d(t,e,n){var a,r,o,i={},l=arguments.length;for(o in e)o=="key"?a=e[o]:o=="ref"&&typeof t!="function"?r=e[o]:i[o]=e[o];return l>2&&(i.children=l>3?pe.call(arguments,2):n),F(t,i,a,r,null)}function F(t,e,n,a,r){var o={type:t,props:e,key:n,ref:a,__k:null,__:null,__b:0,__e:null,__c:null,constructor:void 0,__v:r||++xe,__i:-1,__u:0};return!r&&v.vnode&&v.vnode(o),o}function Z(t){return t.children}function ee(t,e){this.props=t,this.context=e,this.__g=0}function j(t,e){if(e==null)return t.__?j(t.__,t.__i+1):null;for(var n;e<t.__k.length;e++)if((n=t.__k[e])&&n.__e)return n.__e;return typeof t.type!="function"||t.props.__P?null:j(t)}function $e(t){if((t=t.__)&&t.__c&&!t.props.__P)return t.__e=null,t.__k.some(function(e){return e&&(t.__e=e.__e)}),$e(t)}function Ce(t){(8&t.__g||!(t.__g|=8)||!N.push(t)||V++)&&ve==v.debounceRendering||((ve=v.debounceRendering)||queueMicrotask)(Je)}function Je(){var t,e,n,a,r,o,i,l,_;try{for(e=1;N.length;)N.length>e&&N.sort(we),t=N.shift(),e=N.length,8&t.__g&&(a=void 0,r=void 0,o=(r=(n=t).__v).__e,i=[],l=[],(_=n.__P)&&((a=W({constructor:void 0},r)).__v=r.__v+1,v.vnode&&v.vnode(a),ue(_,a,r,n.__n,_.namespaceURI,32&r.__u?[o]:null,i,o||j(r),32&r.__u,l),a.__v=r.__v,a.__.__k[a.__i]=a,Te(i,a,l),r.__=r.__e=null,a.__e!=o&&$e(a)))}finally{N.length=V=0}}function Me(t,e,n,a,r,o,i,l,_,p,c){var y,f,h,u,s,w,x=a.__k||X,$=e.length;for(_=Ve(n,e,x,_,$),y=0;y<$;y++)(h=n.__k[y])!=null&&(f=~h.__i&&x[h.__i]||Y,h.__i=y,w=ue(t,h,f,r,o,i,l,_,p,c),u=h.__e,(f.ref!=h.ref||8&f.__u)&&(f.ref&&fe(f.ref,null,h,f),h.ref&&c.push(h.ref,h.__c||u,h)),s=s||u,4&h.__u?(_=Ae(h,_,t,!f.__v),f.__e&&(f.__e=null)):typeof h.type=="function"&&w!==void 0?_=w:u&&(_=u.nextSibling),h.__u&=-7);return n.__e=s,_}function Ve(t,e,n,a,r){var o,i,l,_,p,c,y,f,h,u,s=n.length,w=s,x=0,$=!1,b=t.__k=Array(r);for(o=0;o<r;o++)(i=e[o])!=null&&typeof i!="boolean"&&typeof i!="function"?(typeof i!="object"||i.constructor==String?i=b[o]=F(null,i):de(i)?i=b[o]=F(Z,{children:i}):i.constructor===void 0&&i.__b?i=b[o]=F(i.type,i.props,i.key,i.ref,i.__v):b[o]=i,_=o+x,i.__=t,i.__b=t.__b+1,l=null,~(p=i.__i=Ge(i,n,_,w))&&(w--,(l=n[p])&&(l.__u|=2)),l&&l.__v?(i.__u|=2,p==_-1?x--:p==_+1?x++:p!=_&&(p>_?x--:x++,$=!0)):(~p||(r>s?x--:r<s&&x++),typeof i.type!="function"&&(i.__u|=4))):b[o]=null;if($){for(c=[],y=[],o=0;o<r;o++)if((i=b[o])&&2&i.__u){for(f=0,h=c.length;f<h;)c[u=f+h>>1]<i.__i?f=u+1:h=u;c[f]=i.__i,y[o]=f+1}for(x=c.length;o--;)y[o]&&(y[o]==x?x--:b[o].__u|=4)}if(w)for(o=0;o<s;o++)!(l=n[o])||2&l.__u||(l.__e==a&&(a=j(l)),he(l,l));return a}function Ae(t,e,n,a){var r,o,i;if(typeof t.type=="function"){if(t.props.__P)return e;if(r=t.__k)for(o=0;o<r.length;o++)r[o]&&(r[o].__=t,e=Ae(r[o],e,n,!1));return e}for(e&&!e.parentNode&&(e=j(t))&&!e.parentNode&&(e=null),i=e;i&&i.nodeType==8;)i=i.nextSibling;for(t.__e!=i&&(!a&&n.moveBefore&&t.__e.parentNode?n.moveBefore(t.__e,e):n.insertBefore(t.__e,e||null)),e=t.__e;(e=e&&e.nextSibling)&&e.nodeType==8;);return e}function Ge(t,e,n,a){var r,o,i,l=t.key,_=t.type,p=e[n],c=p&&!(2&p.__u);if(p===null&&l==null||c&&l==p.key&&_==p.type)return n;if(a>(c?1:0)){for(r=n-1,o=n+1;r>=0||o<e.length;)if((p=e[i=r>=0?r--:o++])&&!(2&p.__u)&&l==p.key&&_==p.type)return i}return-1}function Pe(t,e,n){n==null&&(n=""),e[0]=="-"?t.setProperty(e,n):t[e]=n}function te(t,e,n,a,r){var o,i;e:if(e=="style")if(typeof n=="string")t.style.cssText=n;else{if(typeof a=="string"&&(t.style.cssText=a=""),a)for(e in a)n&&e in n||Pe(t.style,e,"");if(n)for(e in n)a&&n[e]==a[e]||Pe(t.style,e,n[e])}else if(e[0]=="o"&&e[1]=="n")(t.__e||(t.__e={}))[e]=n,n&&a||(i=_e[e]||(_e[e]=Ye(e)),(t.__a||(t.__a={}))[e]=ce,o=e!=(e=e.replace(Se,"$1")),(e=e.slice(2))[0]<"a"&&(e=e.toLowerCase()),n?t.addEventListener(e,i,o):t.removeEventListener(e,i,o));else{if(r=="http://www.w3.org/2000/svg")e=e.replace(/xlink(H|:h)/,"h").replace(/sName$/,"s");else if(e!="width"&&e!="height"&&e!="href"&&e!="list"&&e!="form"&&e!="tabIndex"&&e!="download"&&e!="rowSpan"&&e!="colSpan"&&e!="role"&&e!="popover"&&e in t)try{t[e]=n??"";break e}catch{}typeof n=="function"||(n==null||n===!1&&e[4]!="-"?t.removeAttribute(e):t.setAttribute(e,e=="popover"&&n==1?"":n))}}function Ye(t){return function(e){if(this.__e){var n=this.__e[t];if(e[G]==null)e[G]=ce++;else if(e[G]<this.__a[t])return;return n(v.event?v.event(e):e)}}}function ue(t,e,n,a,r,o,i,l,_,p){var c,y,f,h,u,s,w,x,$,b,m,C,H,R,J,O,L,g,k,P,I=e.type;if(e.constructor!==void 0)return null;if(128&n.__u&&(_=32&n.__u,c=n.__c.__z)){if(e.__u|=_,y=o=[],c.nodeType==8)for(f=1,h=c.nextSibling;h;h=h.nextSibling){if(h.nodeType==8){if(h.data.startsWith("$s"))f++;else if(h.data.startsWith("/$s")&&!--f)break}o.push(h)}else o.push(c);l=o[0]}(c=v.__b)&&c(e);e:if(typeof I=="function"){u=i.length;try{if(b=e.props,m=(c=I.prototype)&&c.render,C=(c=I.contextType)&&a[c.__c],H=c?C?C.props.value:c.__:a,n.__c?2&(s=e.__c=n.__c).__g&&(s.__g|=1):(m?e.__c=s=new I(b,H):(e.__c=s=new ee(b,H),s.constructor=I,s.render=Qe),C&&C.sub(s),s.state||(s.state={}),s.__n=a,s.__g|=8,s.__h=[],s.__k=[]),m&&(s.__s||(s.__s=s.state),I.getDerivedStateFromProps&&(s.__s==s.state&&(s.__s=W({},s.__s)),W(s.__s,I.getDerivedStateFromProps(b,s.__s)))),w=s.props,x=s.state,s.__v=e,n.__c){if(m&&!I.getDerivedStateFromProps&&b!==w&&s.componentWillReceiveProps&&s.componentWillReceiveProps(b,H),e.__v==n.__v&&!(8&s.__g)||!(4&s.__g)&&s.shouldComponentUpdate&&s.shouldComponentUpdate(b,s.__s,H)===!1){e.__v!=n.__v&&(s.props=b,s.state=s.__s,s.__g&=-9),e.__e=n.__e,e.__k=n.__k,e.__k.some(function(S){S&&(S.__=e)}),X.push.apply(s.__h,s.__k),s.__k=[],s.__h.length&&i.push(s),l=j(n);break e}s.componentWillUpdate&&s.componentWillUpdate(b,s.__s,H),m&&s.componentDidUpdate&&s.__h.push(function(){s.componentDidUpdate(w,x,$)})}else m&&!I.getDerivedStateFromProps&&s.componentWillMount&&s.componentWillMount(),m&&s.componentDidMount&&s.__h.push(s.componentDidMount);if(s.context=H,s.props=b,s.__P=t,s.__g&=-5,R=v.__r,J=0,m)s.state=s.__s,s.__g&=-9,R&&R(e),c=s.render(s.props,s.state,s.context),X.push.apply(s.__h,s.__k),s.__k=[];else do s.__g&=-9,R&&R(e),c=s.render(s.props,s.state,s.context),s.state=s.__s;while(8&s.__g&&++J<25);s.state=s.__s,s.getChildContext&&(a=W({},a,s.getChildContext())),m&&n.__c&&s.getSnapshotBeforeUpdate&&($=s.getSnapshotBeforeUpdate(w,x)),O=c&&c.type===Z&&c.key==null?c.props.children:c,b.__P&&(c=l,r=(t=b.__P).namespaceURI,_=o=null,n.props&&n.props.__P!=t&&(n.__k.some(function(S){S&&he(S,S)}),n.__k=null),l=n.__k?j(n,0):null),l=Me(t,de(O)?O:[O],e,n,a,r,o,i,l,_,p),b.__P&&(e.__e=null,l=c),e.__u&=-161,128&n.__u&&(s.__z=null),y&&y.some(Q),s.__h.length&&i.push(s),1&s.__g&&(s.__g&=-4)}catch(S){if(i.length=u,e.__v=null,_||o)if(S.then){if(L=0,e.__u|=_?160:128,o){for(~(k=o.indexOf(l||void 0))||(k=o.length);(P=o[k-1])&&P.nodeType==8;)k--;for(;k<o.length;k++)if(P=o[k]){if(o[k]=null,P.nodeType==8){if(P.data.startsWith("$s"))L++||(g=P);else if(L&&P.data.startsWith("/$s")&&!--L){l=P;break}}else if(!L)break}}if(!g){for(;l&&l.nodeType==8&&l.nextSibling;)l=l.nextSibling;g=l}e.__c.__z||(e.__c.__z=g),e.__e=l}else o&&o.some(Q);else e.__e=n.__e;e.__k||(e.__k=n.__k||[]),S.then||Ie(e),v.__e(S,e,n)}}else l=e.__e=Xe(n.__e,e,n,a,r,o,i,_,p,t);return(c=v.diffed)&&c(e),128&e.__u?void 0:l}function Ie(t){t&&(t.__c&&(t.__c.__g|=4),t.__k&&t.__k.some(Ie))}function Te(t,e,n){for(var a=0;a<n.length;)fe(n[a++],n[a++],n[a++]);v.__c&&v.__c(e,t),t.some(function(r){try{t=r.__h,r.__h=[],t.some(function(o){o.call(r)})}catch(o){v.__e(o,r.__v)}})}function Xe(t,e,n,a,r,o,i,l,_,p){var c,y,f,h,u,s,w,x,$,b=n.props||Y,m=e.props,C=e.type;if(C=="svg"?r="http://www.w3.org/2000/svg":C=="math"?r="http://www.w3.org/1998/Math/MathML":r||(r="http://www.w3.org/1999/xhtml"),o){for(c=0;c<o.length;c++)if((u=o[c])&&(C?u.localName==C:u.nodeType==3)){t=u,o[c]=null;break}}if(!t){if(x=p.ownerDocument||document,!C)return x.createTextNode(m);t=x.createElementNS(r,C,m.is&&m),l&&(v.__m&&v.__m(e,o),l=!1),o=null}if(C){if(p=C=="template"?t.content:t,o=C=="textarea"&&m.defaultValue!=null?null:o&&pe.call(p.childNodes),!l&&o)for(b={},c=0;c<t.attributes.length;c++)b[(u=t.attributes[c]).name]=u.value;for(c in b)u=b[c],c=="dangerouslySetInnerHTML"?f=u:c=="children"||c in m||c=="value"&&"defaultValue"in m||c=="checked"&&"defaultChecked"in m||te(t,c,null,u,r);for(c in $=1&n.__u,m)u=m[c],c=="children"?h=u:c=="dangerouslySetInnerHTML"?y=u:c=="value"?s=u:c=="checked"?w=u:l&&typeof u!="function"||!(b[c]!==u||$&&u!=null)||te(t,c,u,b[c],r);y?(l||f&&(y.__html==f.__html||y.__html==t.innerHTML)||(t.innerHTML=y.__html),e.__k=[]):(f&&(t.textContent=""),(C=="foreignObject"||r=="http://www.w3.org/1998/Math/MathML"&&qe.test(C))&&(r="http://www.w3.org/1999/xhtml"),Me(p,de(h)?h:[h],e,n,a,r,o,i,o?o[0]:n.__k&&j(n,0),l,_),o&&o.some(Q)),l&&C!="textarea"||(c="value",C=="progress"&&s==null?t.removeAttribute(c):s==null||s===t[c]&&(C!="progress"||s)||te(t,c,s,b[c],r),c="checked",w!=null&&w!=t[c]&&te(t,c,w,b[c],r))}else b===m||l&&t.data==m||(t.data=m);return t}function fe(t,e,n,a){try{typeof t=="function"?e?e.__x=t(e)||1:a&&(a=a.__c||a.__e)&&(e=a.__x)&&(a.__x=null,typeof e=="function"?e():t(null)):t.current=e}catch(r){v.__e(r,n)}}function he(t,e,n){var a,r;if(v.unmount&&v.unmount(t),!(a=t.ref)||a.current&&a.current!=t.__e||fe(a,null,e,t),a=t.__c){if(a.componentWillUnmount)try{a.componentWillUnmount()}catch(o){v.__e(o,e)}a.__P=a.__n=null}if(a=t.__k)for(r=0;r<a.length;r++)a[r]&&he(a[r],e,typeof t.type!="function"||n&&!t.props.__P);(a=t.__e)&&(n||Q(a),a.__e&&(a.__e=null)),t.__e=t.__c=t.__=null}function Qe(t,e,n){return this.constructor(t,n)}function Ze(t,e){var n,a,r,o;v.__&&v.__(t,e),e.nodeType==9&&(e=e.documentElement),a=(n=t&&32&t.__u)?null:e.__k,e.__k=F(Z,{children:[t]}),r=[],o=[],ue(e,e.__k,a||Y,Y,e.namespaceURI,a?null:e.firstChild?pe.call(e.childNodes):null,r,a?a.__e:e.firstChild,n,o),Te(r,e.__k,o),e.__k.props.children=null}v={__e:function(t,e,n,a){for(var r,o,i;e=e.__;)if((r=e.__c)&&!(1&r.__g)){r.__g|=4;try{if((o=r.constructor)&&o.getDerivedStateFromError&&(r.setState(o.getDerivedStateFromError(t)),i=8&r.__g),r.componentDidCatch&&(r.componentDidCatch(t,a||{}),i=8&r.__g),i)return void(r.__g|=2)}catch(l){t=l,i=0}}throw V=0,t}},xe=0,ee.prototype.setState=function(t,e){var n=this.__s;n&&n!=this.state||(n=this.__s=W({},this.state)),typeof t=="function"&&(t=t(W({},n),this.props)),t&&(W(n,t),this.__v&&(e&&this.__k.push(e),Ce(this)))},ee.prototype.forceUpdate=function(t){this.__v&&(this.__g|=4,t&&this.__h.push(t),Ce(this))},ee.prototype.render=Z,N=[],V=0,we=function(t,e){return t.__v.__b-e.__v.__b},G=Symbol(),Se=/(PointerCapture)$|Capture$/i,ce=0,_e={};const ne="dataspeak_widget_";function et(t){try{const e=localStorage.getItem(`${ne}${t}`);if(!e)return null;const n=JSON.parse(e);return Date.now()>n.expiresAt-6e4?(localStorage.removeItem(`${ne}${t}`),null):n}catch{return null}}function tt(t,e){try{localStorage.setItem(`${ne}${t}`,JSON.stringify(e))}catch{}}function nt(t){try{localStorage.removeItem(`${ne}${t}`)}catch{}}async function at(t,e,n){const a=`${t.replace(/\/+$/,"")}/api/widget/session`,r=await fetch(a,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({public_key:e,conversation_id:n})});if(!r.ok){let l="Failed to initialize session";try{l=(await r.json()).detail||l}catch{}throw new Error(l)}const o=await r.json(),i={sessionToken:o.session_token,expiresAt:Date.now()+o.expires_in*1e3,tenantId:o.tenant_id,conversationId:o.conversation_id};return tt(e,i),i}async function ot(t,e){try{const n=`${t.replace(/\/+$/,"")}/api/widget/config?key=${encodeURIComponent(e)}`,a=await fetch(n);if(!a.ok)return{};const r=await a.json();return{themeColor:r.theme_color,widgetTitle:r.widget_title,greetingMessage:r.greeting_message,position:r.position,welcomeDelay:r.welcome_delay,soundEnabled:r.sound_enabled}}catch{return{}}}function De(t){const e=t.trim();if(!e.startsWith("data:"))return null;const n=e.slice(5).trim();if(!n||n==="[DONE]")return null;try{return JSON.parse(n)}catch{return null}}class rt{constructor(){this.buffer=""}feed(e){this.buffer+=e;const n=this.buffer.split(`

`);this.buffer=n.pop()||"";const a=[];for(const r of n){const o=De(r);o&&a.push(o)}return a}flush(){if(!this.buffer.trim())return[];const e=De(this.buffer);return this.buffer="",e?[e]:[]}}async function st(t,e,n,a,r,o,i,l){const _=`${t.replace(/\/+$/,"")}/api/chat/widget`;try{const p=await fetch(_,{method:"POST",signal:l,headers:{"Content-Type":"application/json",Authorization:`Bearer ${e}`,Accept:"text/event-stream"},body:JSON.stringify({query:n,session_token:e,conversation_id:a,stream:!0})});if(p.status===429){const u=p.headers.get("Retry-After"),s=u?parseInt(u,10):5;let w="Too many requests. Please wait before asking again.";try{const x=await p.json();x.detail&&(w=x.detail)}catch{}i(w,s);return}if(!p.ok){let u="Failed to send message";try{const s=await p.json();s.detail&&(u=s.detail)}catch{}i(u);return}if(!p.body){i("No response received from assistant");return}const c=p.body.getReader(),y=new TextDecoder("utf-8"),f=new rt;for(;;){if(l!=null&&l.aborted){try{await c.cancel()}catch{}return}const{done:u,value:s}=await c.read();if(u)break;const w=y.decode(s,{stream:!0}),x=f.feed(w);for(const $ of x)$.error&&i($.error),$.chunk&&r($.chunk),$.done&&o({conversationId:$.conversation_id||a,messageId:$.message_id,sources:$.sources||[]})}const h=f.flush();for(const u of h)u.error&&i(u.error),u.chunk&&r(u.chunk),u.done&&o({conversationId:u.conversation_id||a,messageId:u.message_id,sources:u.sources||[]})}catch(p){if(p.name==="AbortError"||l!=null&&l.aborted)return;i(p.message||"Network connection error")}}function ae(t="#3b82f6",e="bottom-right"){const n=e==="bottom-left",a=n?"bottom: 20px; left: 20px;":"bottom: 20px; right: 20px;";return`
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
`}function it(t="#3b82f6",e="bottom-right"){const n=document.createElement("div");n.id="dataspeak-chatbot-widget-root",n.style.setProperty("display","block","important"),n.style.setProperty("visibility","visible","important"),n.style.setProperty("position","fixed","important"),n.style.setProperty("z-index","2147483647","important"),n.style.setProperty("border","none","important"),n.style.setProperty("margin","0","important"),n.style.setProperty("padding","0","important"),n.style.setProperty("width","0","important"),n.style.setProperty("height","0","important"),n.style.setProperty("overflow","visible","important");const a=n.attachShadow({mode:"open"});let r;if("adoptedStyleSheets"in a&&typeof CSSStyleSheet<"u"&&"replaceSync"in CSSStyleSheet.prototype){const i=new CSSStyleSheet;i.replaceSync(ae(t,e)),a.adoptedStyleSheets=[i],r=(l,_)=>{i.replaceSync(ae(l,_))}}else{const i=document.createElement("style");i.textContent=ae(t,e),a.appendChild(i),r=(l,_)=>{i.textContent=ae(l,_)}}const o=document.createElement("div");return o.id="dataspeak-widget-app",a.appendChild(o),document.body.appendChild(n),{host:n,shadowRoot:a,mountContainer:o,updateStyles:r}}var K,A,ge,He,be=Object.is,oe=0,ze=[],me=[],M=v,Ne=M.__b,je=M.__r,Ee=M.diffed,Le=M.__c,We=M.unmount,Re=M.__;function ye(t,e){M.__h&&M.__h(A,t,oe||e),oe=0;var n=A.__H||(A.__H={__:[],__h:[]});return t>=n.__.length&&n.__.push({}),n.__[t]}function E(t){return oe=1,lt(Fe,t)}function lt(t,e,n){var a=ye(K++,2);if(a.t=t,!a.__c&&(a.__=[Fe(void 0,e),function(o){var i=a.__N?a.__N[0]:a.__[0],l=a.t(i,o);be(i,l)||(a.__N=[l,a.__[1]],a.__c.setState({}))}],a.__c=A,!A.__f)){A.__f=!0;var r=A.shouldComponentUpdate;A.shouldComponentUpdate=function(o,i,l){var _=this.__H;if(!_)return!0;var p=!1,c=this.props!=o;if(_.__.some(function(f){f.__N&&(p=!0,be(f.__[0],f.__N[0])||(c=!0))}),r){var y=r.call(this,o,i,l);return p?y||c:y}return!p||c}}return a.__}function B(t,e){var n=ye(K++,3);!M.__s&&Oe(n.__H,e)&&(n.__P=!0,n.__=t,n.u=e,A.__H.__h.push(n))}function re(t){return oe=5,ct(function(){return{current:t}},[])}function ct(t,e){var n=ye(K++,7);return Oe(n.__H,e)&&(n.__=t(),n.__H=e),n.__}function _t(){var t;do{for(;t=me.shift();)try{q(t)}catch(n){M.__e(n,{__:(t=t.__P)&&t.__v})}for(;t=ze.shift();){var e=t.__H;if(t.__P&&e)try{e.__h.some(q),e.__h.some(ke),e.__h=[]}catch(n){e.__h=[],M.__e(n,t.__v)}}}while(me.length)}M.__b=function(t){A=null,Ne&&Ne(t)},M.__=function(t,e){t&&e.__k&&e.__k.__m&&(t.__m=e.__k.__m),Re&&Re(t,e)},M.__r=function(t){je&&je(t),K=0;var e=(A=t.__c).__H;e&&(ge==A?A.__h=[]:(e.__h.some(q),e.__h.some(ke),K=0),e.__h=[],e.__.some(function(n){n.__N&&(n.__=n.__N),n.u=n.__N=void 0})),ge=A},M.diffed=function(t){Ee&&Ee(t);var e=t.__c;e&&e.__H&&(e.__H.__h.length&&Be(ze.push(e)),e.__H.__.some(function(n){n.u&&(n.__H=n.u)})),ge=A=null},M.__c=function(t,e){e.some(function(n){try{n.__h.some(q),n.__h=n.__h.filter(function(a){return!a.__||ke(a)})}catch(a){e.some(function(r){r.__h&&(r.__h=[])}),e=[],M.__e(a,n.__v)}}),Le&&Le(t,e)},M.unmount=function(t){We&&We(t);var e,n,a=t.__c;a&&a.__H&&(a.__H.__.some(function(r){try{if(r.__P&&r.__c){if(n===void 0){for(n=t.__;n&&(!n.__c||!n.__c.__P);)n=n.__;n=n&&n.__c}r.__P=n,Be(me.push(r))}else q(r)}catch(o){e=o}}),a.__H=void 0,e&&M.__e(e,a.__v))};var Ue=typeof requestAnimationFrame=="function";function dt(t){var e,n=function(){clearTimeout(a),Ue&&cancelAnimationFrame(e),setTimeout(t)},a=setTimeout(n,35);Ue&&(e=requestAnimationFrame(n))}function Be(t){t!=1&&He==M.requestAnimationFrame||((He=M.requestAnimationFrame)||dt)(_t)}function q(t){var e=A,n=t.__c;typeof n=="function"&&(t.__c=void 0,n()),A=e}function ke(t){var e=A;t.__c=t.__(),A=e}function Oe(t,e){return!t||t.length!=e.length||e.some(function(n,a){return!be(n,t[a])})}function Fe(t,e){return typeof e=="function"?e(t):e}function pt(t){try{const e=new URL(t,"https://dummy-base-domain.internal");return e.protocol==="http:"||e.protocol==="https:"}catch{return!1}}function se(t){const e=[];let n=t,a=0;for(;n.length>0;){const r=n.match(/^\[([^\]]+)\]\(([^)]+)\)/);if(r){const c=r[1],y=r[2].trim();pt(y)?e.push(d("a",{key:`lnk-${a++}`,href:y,target:"_blank",rel:"noopener noreferrer"},c)):e.push(c),n=n.slice(r[0].length);continue}const o=n.match(/^(\*\*|__)(.*?)\1/);if(o&&o[2]){e.push(d("strong",{key:`b-${a++}`},se(o[2]))),n=n.slice(o[0].length);continue}const i=n.match(/^`([^`]+)`/);if(i&&i[1]){e.push(d("code",{key:`code-${a++}`},i[1])),n=n.slice(i[0].length);continue}const l=n.match(/^(\*|_)(.*?)\1/);if(l&&l[2]){e.push(d("em",{key:`em-${a++}`},se(l[2]))),n=n.slice(l[0].length);continue}const _=n.match(/^\[Source:\s*([^\]]+)\]/);if(_&&_[1]){e.push(d("span",{key:`cit-${a++}`,class:"dataspeak-source-badge"},`📄 ${_[1]}`)),n=n.slice(_[0].length);continue}const p=n.search(/(\[|\*\*|__|`|\*|_)/);if(p===-1){e.push(n);break}else p===0?(e.push(n[0]),n=n.slice(1)):(e.push(n.slice(0,p)),n=n.slice(p))}return e}function ut({content:t}){if(!t)return d("span",null,"");const e=t.split(`
`),n=[];let a=[],r=0;for(let o=0;o<e.length;o++){const i=e[o],l=i.trim(),_=l.match(/^[-*]\s+(.*)$/);if(_){a.push(d("li",{key:`li-${r}-${a.length}`},se(_[1])));continue}a.length>0&&(n.push(d("ul",{key:`ul-${r++}`},a)),a=[]),l.length!==0&&n.push(d("p",{key:`p-${r++}`},se(i)))}return a.length>0&&n.push(d("ul",{key:`ul-${r++}`},a)),d("div",{class:"dataspeak-markdown-body"},n)}function ft({initialConfig:t}){var L;const[e,n]=E(!1),[a,r]=E(t),[o,i]=E(null),[l,_]=E([]),[p,c]=E(""),[y,f]=E(!1),[h,u]=E(null),[s,w]=E(null),x=re(null),$=re(null),b=re(null),m=re(null);B(()=>()=>{var g;(g=m.current)==null||g.abort()},[]),B(()=>{let g=et(a.publicKey);g&&i(g);const k=a.greetingMessage||"Hello! How can I help you today?";_([{id:"msg-greeting",role:"assistant",text:k}])},[a.publicKey]),B(()=>{x.current&&x.current.scrollIntoView({behavior:"smooth"})},[l,y]),B(()=>{var g;e?setTimeout(()=>{var k;return(k=$.current)==null?void 0:k.focus()},150):(g=b.current)==null||g.focus()},[e]),B(()=>{const g=k=>{k.key==="Escape"&&e&&n(!1)};return window.addEventListener("keydown",g),()=>window.removeEventListener("keydown",g)},[e]),B(()=>{if(s===null||s<=0)return;const g=setTimeout(()=>{w(k=>k&&k>1?k-1:null)},1e3);return()=>clearTimeout(g)},[s]);const C=()=>{n(!e),u(null)},H=()=>{m.current&&(m.current.abort(),m.current=null),f(!1),_(g=>g.map((k,P)=>P===g.length-1&&k.role==="assistant"?{...k,isStreaming:!1,text:k.text?k.text+`

*(Generation stopped)*`:"*(Generation cancelled)*"}:k))},R=async()=>{m.current&&(m.current.abort(),m.current=null),f(!1),nt(a.publicKey),i(null),_([{id:`msg-greeting-${Date.now()}`,role:"assistant",text:a.greetingMessage||"Hello! How can I help you today?"}]),u(null)},J=async()=>{const g=p.trim();if(!g||y||s!==null)return;c(""),u(null);const k=`user-${Date.now()}`,P=`asst-${Date.now()}`;_(S=>[...S,{id:k,role:"user",text:g},{id:P,role:"assistant",text:"",isStreaming:!0}]),f(!0);const I=new AbortController;m.current=I;try{let S=o;(!S||Date.now()>S.expiresAt-6e4)&&(S=await at(a.apiBase,a.publicKey,S==null?void 0:S.conversationId),i(S)),await st(a.apiBase,S.sessionToken,g,S.conversationId,U=>{_(z=>z.map(D=>D.id===P?{...D,text:D.text+U}:D))},U=>{m.current=null,f(!1),_(z=>z.map(D=>D.id===P?{...D,isStreaming:!1,sources:U.sources}:D))},(U,z)=>{m.current=null,f(!1),u(U),z&&w(z),_(D=>D.filter(Ke=>!(Ke.id===P&&!Ke.text)))},I.signal)}catch(S){m.current=null,f(!1),S.name!=="AbortError"&&!I.signal.aborted&&u(S.message||"Unable to establish secure connection"),_(U=>U.filter(z=>!(z.id===P&&!z.text)))}},O=g=>{g.key==="Enter"&&!g.shiftKey&&(g.preventDefault(),J())};return d("div",{class:"dataspeak-container"},[d("button",{ref:b,class:"dataspeak-launcher",onClick:C,"aria-label":e?"Close chat assistant":"Open chat assistant","aria-expanded":e},e?d("svg",{viewBox:"0 0 24 24",fill:"none",stroke:"currentColor","stroke-width":"2"},d("path",{d:"M18 6L6 18M6 6l12 12"})):d("svg",{viewBox:"0 0 24 24",fill:"none",stroke:"currentColor","stroke-width":"2"},[d("path",{d:"M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"})])),d("div",{class:`dataspeak-panel ${e?"open":""}`,role:"dialog","aria-modal":"true","aria-label":a.widgetTitle||"AI Assistant","aria-hidden":e?"false":"true"},[d("div",{class:"dataspeak-header"},[d("div",{class:"dataspeak-header-left"},[d("div",{class:"dataspeak-avatar"},"AI"),d("div",null,[d("div",{class:"dataspeak-header-title"},a.widgetTitle||"AI Assistant"),d("div",{class:"dataspeak-header-status"},[d("span",{class:"dataspeak-status-dot"}),"Online"])])]),d("div",{class:"dataspeak-header-actions"},[d("button",{class:"dataspeak-icon-btn",onClick:R,title:"Start new chat","aria-label":"Start new chat"},d("svg",{width:"18",height:"18",viewBox:"0 0 24 24",fill:"none",stroke:"currentColor","stroke-width":"2"},d("path",{d:"M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8M21 3v5h-5M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16M3 21v-5h5"}))),d("button",{class:"dataspeak-icon-btn",onClick:()=>n(!1),title:"Close chat","aria-label":"Close chat"},d("svg",{width:"18",height:"18",viewBox:"0 0 24 24",fill:"none",stroke:"currentColor","stroke-width":"2"},d("path",{d:"M18 6L6 18M6 6l12 12"})))])]),d("div",{class:"dataspeak-messages","aria-live":"polite"},[...l.map(g=>d("div",{key:g.id,class:`dataspeak-msg-row ${g.role}`},[d("div",{class:"dataspeak-bubble"},g.role==="assistant"?d(ut,{content:g.text}):g.text),g.sources&&g.sources.length>0?d("div",{class:"dataspeak-sources"},g.sources.map((k,P)=>d("span",{key:`src-${P}`,class:"dataspeak-source-badge"},`📄 ${k.document_name}${k.page_number?` (p. ${k.page_number})`:""}`))):null])),y&&((L=l[l.length-1])==null?void 0:L.text)===""?d("div",{class:"dataspeak-typing","aria-label":"Assistant is thinking"},[d("span",{class:"dataspeak-dot"}),d("span",{class:"dataspeak-dot"}),d("span",{class:"dataspeak-dot"})]):null,d("div",{ref:x})]),h?d("div",{class:"dataspeak-error-banner"},[d("span",null,h),s!==null?d("span",{class:"dataspeak-countdown"},` (${s}s)`):null]):null,d("div",{class:"dataspeak-footer"},[d("div",{class:"dataspeak-input-row"},[d("textarea",{ref:$,class:"dataspeak-input",placeholder:s!==null?`Rate limit active... wait ${s}s`:"Type a message...",value:p,disabled:s!==null,rows:1,onInput:g=>c(g.target.value),onKeyDown:O}),y?d("button",{class:"dataspeak-stop-btn",onClick:H,"aria-label":"Stop generation",title:"Stop generation"},d("svg",{width:"14",height:"14",viewBox:"0 0 24 24",fill:"currentColor"},d("rect",{x:"4",y:"4",width:"16",height:"16",rx:"2"}))):d("button",{class:"dataspeak-send-btn",onClick:J,disabled:!p.trim()||s!==null,"aria-label":"Send message"},d("svg",{width:"16",height:"16",viewBox:"0 0 24 24",fill:"none",stroke:"currentColor","stroke-width":"2.5"},d("path",{d:"M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"})))]),d("div",{class:"dataspeak-branding"},["Powered by ",d("a",{href:"https://dataspeak.ai",target:"_blank",rel:"noopener noreferrer"},"DataSpeakAI")])])])])}const T=document.currentScript||null;function ht(){let t="",e=window.location.origin,n="#3b82f6",a="AI Assistant",r="Hello! How can I help you today?",o="bottom-right",i=1,l=!1;if(T){t=T.getAttribute("data-key")||"";const _=T.src;if(_)try{e=new URL(_).origin}catch{}const p=T.getAttribute("data-api");p&&(e=p),T.getAttribute("data-theme")&&(n=T.getAttribute("data-theme")),T.getAttribute("data-title")&&(a=T.getAttribute("data-title")),T.getAttribute("data-position")&&(o=T.getAttribute("data-position")),T.getAttribute("data-welcome")&&(r=T.getAttribute("data-welcome"))}return{publicKey:t,apiBase:e,themeColor:n,widgetTitle:a,greetingMessage:r,position:o,welcomeDelay:i,soundEnabled:l}}function ie(t){const n={...ht(),...t};if(!n.publicKey){console.warn("[DataSpeakAI] Missing data-key on widget script. Widget initialization aborted.");return}if(document.getElementById("dataspeak-chatbot-widget-root"))return;const a=it(n.themeColor,n.position);return Ze(d(ft,{initialConfig:n}),a.mountContainer),ot(n.apiBase,n.publicKey).then(r=>{if(r.themeColor||r.position){const o=n.themeColor||r.themeColor||"#3b82f6",i=n.position||r.position||"bottom-right";a.updateStyles(o,i)}}).catch(()=>{}),a}return typeof window<"u"&&(document.readyState==="loading"?document.addEventListener("DOMContentLoaded",()=>ie()):ie(),window.DataSpeakAI={init:ie,version:"1.0.0"}),le.initWidget=ie,Object.defineProperty(le,Symbol.toStringTag,{value:"Module"}),le})({});
