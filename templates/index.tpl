{% args avg, min, max, bmpb64, minimage, maximage, refreshms %}
<!DOCTYPE html>
<html>
<head>
  <title>IR image</title>
</head>
<body>

<a href="/bmp"><img id="irimage" src="data:image/bmp;base64,{{bmpb64}}" alt="IR image" width="512" height="512"></a>
<br>

<p id="avg">Average: {{avg}}</p>
<p id="min">Min: {{min}}</p>
<p id="max">Max: {{max}}</p>

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

var irimage = document.getElementById("irimage");

function refreshBMP() {
  var xhr = new XMLHttpRequest();
  xhr.onload = function() {
    var reader = new FileReader();
    reader.onloadend = function() {
      irimage.src = reader.result;
    }
    reader.readAsDataURL(xhr.response);
    document.getElementById("avg").innerHTML = 'Average: '+xhr.getResponseHeader('x-pixavg');
    document.getElementById("min").innerHTML = 'Min: '+xhr.getResponseHeader('x-pixmin');
    document.getElementById("max").innerHTML = 'Max: '+xhr.getResponseHeader('x-pixmax');
    setTimeout(refreshBMP, {{refreshms}});
  };
  xhr.open('GET', "/bmp?mindegC={{minimage}}&maxdegC={{maximage}}&stats=1&time=" + new Date().getTime());
  xhr.responseType = 'blob';
  xhr.send();
}

setTimeout(refreshBMP, {{refreshms}});

</script>
{% endif %}

</body>
</html>