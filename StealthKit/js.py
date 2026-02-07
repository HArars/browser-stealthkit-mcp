# stealth_kit/js.py

# Core stealth script: remove webdriver flag, mock chrome object, patch permissions.
STEALTH_JS = """
// 1. Remove navigator.webdriver (including prototype chain)
const newProto = navigator.__proto__;
delete newProto.webdriver;
navigator.__proto__ = newProto;

// 2. Mock window.chrome to look like regular Chrome/Edge
if (window.chrome === undefined) {
    window.chrome = {
        runtime: {},
        loadTimes: function() {},
        csi: function() {},
        app: {}
    };
}

// 3. Patch Permissions API behavior
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
    Promise.resolve({ state: Notification.permission }) :
    originalQuery(parameters)
);

// 4. Override WebGL vendor/renderer values (optional)
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
