from unittest.mock import patch
from app import get_db

def test_signup_success(client):
    with patch("app.send_verification_email") as mock_send_email:
        mock_send_email.return_value = None

        db = get_db()
        db.execute("DELETE FROM users WHERE email = ?", ("user@example.com",))
        db.commit()

        response = client.post('/signup', data={
            'email': 'info@vsteschenko.me',
            'password': 'testpassword'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'login' in response.data or b'Login' in response.data

        user = db.execute("SELECT * FROM users WHERE email = ?", ("info@vsteschenko.me",)).fetchone()
        assert user is not None

        mock_send_email.assert_called_once()