{% args avg, min, max, bmpb64, minimage, maximage %}
<!DOCTYPE html>
<html>
<head>
  <title>IR image</title>
</head>
<body>

<a href="/bmp"><img src="data:image/bmp;base64,{{bmpb64}}" alt="IR image" width="512" height="512"></a>
<br>
Average: {{avg}}<br>
Min: {{min}}<br>
Max: {{max}}<br>

<form action="/index.html" method="GET">
  <label for="min">Image Min:</label><br>
  <input type="text" id="min" name="min" value="{{minimage}}"><br>
  <label for="max">Image Max:</label><br>
  <input type="text" id="max" name="max" value="{{maximage}}"><br>
  <input type="submit" />
</form>

</body>
</html>