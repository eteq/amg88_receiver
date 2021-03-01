{% args avg, min, max, bmpb64, minimage, maximage, refreshms %}
<!DOCTYPE html>
<html>
<head>
  <title>IR image</title>
</head>
<body>

<a href="/bmp"><img id="irimage" src="data:image/bmp;base64,{{bmpb64}}" alt="IR image" width="512" height="512"></a>
<br>
Average: {{avg}}<br>
Min: {{min}}<br>
Max: {{max}}<br>

<form action="/index.html" method="GET">
  <label for="min">Image Min:</label><br>
  <input type="text" id="min" name="min" value="{{minimage}}"><br>
  <label for="max">Image Max:</label><br>
  <input type="text" id="max" name="max" value="{{maximage}}"><br>
  <label for="refreshms">Auto refresh time (ms):</label><br>
  <input type="text" id="refreshms" name="refreshms" value="{{refreshms}}"><br>
  <input type="submit" />
</form>
{% if refreshms >= 0 %}
<script>
function refreshBMP() {
  var irimage = document.getElementById("irimage");
  if (irimage.complete) {
    irimage.src = "/bmp?mindegC={{minimage}}&maxdegC={{maximage}}&" + new Date().getTime();
  }
  setTimeout(refreshBMP, {{refreshms}});
}
setTimeout(refreshBMP, {{refreshms}});
</script>
{% endif %}

</body>
</html>