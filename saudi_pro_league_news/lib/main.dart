import 'package:flutter/material.dart';
import 'pages/news_page.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false, // 🚫 remove the debug banner
      title: 'Saudi Football News',
      theme: ThemeData(
        primarySwatch: Colors.green,
        useMaterial3: true, // ✅ smoother UI on Flutter 3+
        visualDensity: VisualDensity.adaptivePlatformDensity, // ✅ adaptive spacing
      ),
      home: const NewsPage(),
    );
  }
}
