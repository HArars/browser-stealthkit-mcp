# stealth_kit/js.py

# 核心去特征脚本：移除 webdriver，伪造 chrome 对象，修复 permissions
STEALTH_JS = """
// 1. 彻底移除 navigator.webdriver (包括原型链)
const newProto = navigator.__proto__;
delete newProto.webdriver;
navigator.__proto__ = newProto;

// 2. 伪造 window.chrome (让网页觉得是正版 Chrome/Edge)
if (window.chrome === undefined) {
    window.chrome = {
        runtime: {},
        loadTimes: function() {},
        csi: function() {},
        app: {}
    };
}

// 3. 欺骗 Permissions API
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
    Promise.resolve({ state: Notification.permission }) :
    originalQuery(parameters)
);

// 4. 伪造 WebGL 厂商 (可选，防止被识别为虚拟机显卡)
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    // 37445: UNMASKED_VENDOR_WEBGL
    // 37446: UNMASKED_RENDERER_WEBGL
    if (parameter === 37445) {
        return 'Google Inc. (Intel)';
    }
    if (parameter === 37446) {
        return 'ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0)';
    }
    return getParameter(parameter);
};
"""