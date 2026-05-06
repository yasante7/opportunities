import requests

def test_link():
    url = "https://wp.me/p23f03-laY"
    response = requests.get(url)
    print(f"Response status code: {response.status_code}")
    assert response.status_code == 200

    assert "Link" in response.text

if __name__ == "__main__":    
    test_link()
    print("Test passed!")