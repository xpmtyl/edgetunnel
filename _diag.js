// 临时诊断：仅验证模块加载是否成功
const H = { 'Content-Type': 'text/plain;charset=utf-8' };
function safe(e) {
	try { return (e && (e.stack || e.message)) ? (e.stack || e.message) : String(e); }
	catch (x) { return '[unstringifiable]'; }
}
export default {
	async fetch(request, env, ctx) {
		const t0 = Date.now();
		let mod;
		try {
			mod = await import('./_worker.js');
		} catch (e) {
			return new Response('DIAG_IMPORT_ERROR after ' + (Date.now() - t0) + 'ms\n' + safe(e), { status: 500, headers: H });
		}
		return new Response('DIAG_IMPORT_OK in ' + (Date.now() - t0) + 'ms\n' +
			'default type: ' + typeof mod.default + '\n' +
			'fetch type: ' + typeof (mod.default && mod.default.fetch) + '\n' +
			'env keys: ' + Object.keys(env).join(','), { status: 200, headers: H });
	}
};
