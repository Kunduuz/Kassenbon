
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import 'package:path_provider/path_provider.dart';

void main() {
  runApp(MaterialApp(
    home: OCRUploader(),
    debugShowCheckedModeBanner: false,
  ));
}

class OCRUploader extends StatefulWidget {
  @override
  _OCRUploaderState createState() => _OCRUploaderState();
}

class _OCRUploaderState extends State<OCRUploader> {
  File? _image;
  String _result = '';
  bool _isLoading = false;

  final String apiUrl = 'https://kassenbon.onrender.com'; // <- später anpassen

  Future<void> _pickImage(ImageSource source) async {
    final picker = ImagePicker();
    final picked = await picker.pickImage(source: source);

    if (picked != null) {
      setState(() {
        _image = File(picked.path);
        _result = '';
      });
      _uploadImage(File(picked.path));
    }
  }

  Future<void> _uploadImage(File image) async {
    setState(() {
      _isLoading = true;
    });

    final uri = Uri.parse(apiUrl);
    final request = http.MultipartRequest('POST', uri);
    request.files.add(await http.MultipartFile.fromPath('file', image.path));

    final response = await request.send();
    final responseBody = await response.stream.bytesToString();

    setState(() {
      _isLoading = false;
      if (response.statusCode == 200) {
        final data = json.decode(responseBody);
        _result = const JsonEncoder.withIndent('  ').convert(data);
      } else {
        _result = "Fehler: ${response.reasonPhrase}";
      }
    });
  }

  Widget _buildImage() {
    return _image == null
        ? Text("Kein Bild ausgewählt")
        : Image.file(_image!, height: 200);
  }

  Widget _buildResult() {
    return SelectableText(
      _result,
      style: TextStyle(fontFamily: 'Courier', fontSize: 14),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Kassenbon OCR Upload'),
        backgroundColor: Colors.deepPurple,
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            _buildImage(),
            const SizedBox(height: 20),
            if (_isLoading) CircularProgressIndicator(),
            if (!_isLoading)
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  ElevatedButton.icon(
                    onPressed: () => _pickImage(ImageSource.camera),
                    icon: Icon(Icons.camera_alt),
                    label: Text("Kamera"),
                  ),
                  const SizedBox(width: 10),
                  ElevatedButton.icon(
                    onPressed: () => _pickImage(ImageSource.gallery),
                    icon: Icon(Icons.photo),
                    label: Text("Galerie"),
                  ),
                ],
              ),
            const SizedBox(height: 20),
            Expanded(child: SingleChildScrollView(child: _buildResult()))
          ],
        ),
      ),
    );
  }
}
