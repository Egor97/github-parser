from logging import StreamHandler, basicConfig, getLogger

from config import settings
from database import init_db_connect, ParserRepository
from service import YandexCloudService

x_format = '%(asctime)s : %(name)s : %(levelname)s : %(message)s'

console_handler = StreamHandler()
console_handler.setLevel('DEBUG')

basicConfig(level='DEBUG', format=x_format, handlers=[console_handler])

logger = getLogger(__name__)


async def main(event, context):
    logger.debug('Start')
    logger.debug('Trying to connect db')
    try:
        session = await init_db_connect()
    except Exception as ex:
        logger.exception(ex)
        return {'status_code': 500,
                'msg': 'Проблема с подключением к базе данных, попробуйте позже'}

    parser_repository = ParserRepository(session)
    yandex_cloud_service = YandexCloudService(settings.API_TOKEN, parser_repository)

    try:
        await yandex_cloud_service.start()
    except Exception as ex:
        logger.exception(ex)
        return {'status_code': 500,
                'detail': 'Проблема с сервером, попробуйте позже'}
    finally:
        await session.close()

    return {'status_code': 200,
            'msg': 'Success'}
