import http.client
import json
 
conn = http.client.HTTPSConnection("api.openai.com")
payload = json.dumps({
  "model": "gpt-4o-mini",
  "messages": [
    {
      "role": "user",
      "content": "Liste todos os presidentes do brasil"
    }
  ]
})
headers = {
  'Content-Type': 'application/json',
  'Authorization': 'Bearer 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',
  'Cookie': '__cf_bm=mSVbwzjskKsG9wWUCd4gy2TafJTXrlF3.eF9THn_UGc-1744376420-1.0.1.1-xvUCgwNi_lM4iycQwJRY..mc2xQVKxUYohi3Z46fBfzCEQ_YsQMflTbZUCHezrfYy2PFUpXdhTZw1riOJ8HO9_vQyzE4b2Jxec5e7dn8mnQ; _cfuvid=w1deGpw6k0lMuHkPmTvDX.6T1XNnFmrgddQJ0aKQXCc-1744376420974-0.0.1.1-604800000'
}
conn.request("POST", "/v1/chat/completions", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))