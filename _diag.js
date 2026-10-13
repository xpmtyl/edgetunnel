// 临时诊断包装器：捕获 _worker.js 的模块加载错误与 fetch 运行时异常
export default {
	async fetch(request, env, ctx) {
		let mod;
		try {
			mod = await import('./_worker.js');
		} catch (e) {
			return new Response('DIAG_IMPORT_ERROR\n' + (e && (e.stack || e.message) || String(e)),
				{ status: 500, headers: { 'Content-Type': 'text/plain;charset=utf-8' } });
		}
		try {
			return await mod.default.fetch(request, env, ctx);
		} catch (e) {
			return new Response('DIAG_FETCH_ERROR\n' + (e && (e.stack || e.message) || String(e)) +
				'\n\n-- env keys: ' + Object.keys(env).join(',') +
				'\n-- cf: ' + JSON.stringify(request.cf),
				{ status: 500, headers: { 'Content-Type': 'text/plain;charset=utf-8' } });
		}
	}
};
