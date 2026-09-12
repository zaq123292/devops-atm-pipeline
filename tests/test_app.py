from conftest import login
def test_pages(client):
    assert client.get('/').status_code == 200
    assert client.get('/login').status_code == 200
    assert client.get('/dashboard').status_code == 302
def test_login_and_injection(client):
    assert login(client).status_code == 302
    response = client.post('/login', data={'card':'10000001', 'pin':"' OR '1'='1"}, follow_redirects=True)
    assert '错误'.encode() in response.data
def test_health(client):
    result = client.get('/health').get_json(); assert result['status'] == 'ok'; assert result['db_status'] == 'connected'
def test_withdraw_and_limits(client):
    login(client); assert client.post('/withdraw', data={'amount':'100'}).status_code == 302
    response = client.post('/withdraw', data={'amount':'6000'}, follow_redirects=True)
    assert response.status_code == 200
def test_deposit_transfer_history(client):
    login(client); assert client.post('/deposit', data={'amount':'200'}).status_code == 302
    assert client.post('/transfer', data={'target':'10000001','amount':'100'}, follow_redirects=True).status_code == 200
    assert client.get('/history').status_code == 200
