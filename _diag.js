export default {
	async fetch(request, env, ctx) {
		return new Response('TRIVIAL_OK host=' + new URL(request.url).host + ' env=' + Object.keys(env).join(','),
			{ status: 200, headers: { 'Content-Type': 'text/plain;charset=utf-8' } });
	}
};
