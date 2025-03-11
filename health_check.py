from aiohttp import web

async def health_check(request):
    return web.Response(text="OK")

app = web.Application()
app.add_routes([web.get('/', health_check)])

if __name__ == "__main__":
    web.run_app(app, port=8000)
