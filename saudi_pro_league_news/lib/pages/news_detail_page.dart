import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../models/news.dart';

class NewsDetailPage extends StatelessWidget {
  final News article;

  const NewsDetailPage({super.key, required this.article});

  /// Parse content and render text + inline media
  List<Widget> _buildContent(BuildContext context) {
    final widgets = <Widget>[];
    final text =
        article.content ?? article.description ?? "No content available";

    final parts = text.split(RegExp(r"\s+"));
    final buffer = StringBuffer();

    for (final word in parts) {
      if (word.startsWith("http")) {
        // Flush previous text
        if (buffer.isNotEmpty) {
          widgets.add(
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Text(
                buffer.toString(),
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ),
          );
          buffer.clear();
        }

        if (word.endsWith(".jpg") ||
            word.endsWith(".jpeg") ||
            word.endsWith(".png") ||
            word.endsWith(".gif")) {
          // Inline image
          widgets.add(
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Image.network(
                word,
                width: double.infinity,
                fit: BoxFit.contain,
              ),
            ),
          );
        } else {
          // Clickable external link
          widgets.add(
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: InkWell(
                onTap: () async {
                  final uri = Uri.tryParse(word);
                  if (uri != null && await canLaunchUrl(uri)) {
                    await launchUrl(uri, mode: LaunchMode.externalApplication);
                  }
                },
                child: Text(
                  word,
                  style: const TextStyle(
                    color: Colors.blue,
                    decoration: TextDecoration.underline,
                  ),
                ),
              ),
            ),
          );
        }
      } else {
        buffer.write("$word ");
      }
    }

    // Add remaining text
    if (buffer.isNotEmpty) {
      widgets.add(
        Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Text(
            buffer.toString(),
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        ),
      );
    }

    return widgets;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey[100],
      appBar: AppBar(
        title: Text(
          article.title,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        centerTitle: true,
        backgroundColor: Colors.green[700],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (article.image != null)
              ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Image.network(
                  article.image!,
                  width: double.infinity,
                  fit: BoxFit.cover,
                ),
              ),
            const SizedBox(height: 16),
            Text(
              article.title,
              style: Theme.of(
                context,
              ).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 6),
            Text(
              "${article.publishedAt!.toLocal()}".split(" ")[0],
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: Colors.grey[600]),
            ),
            const SizedBox(height: 16),
            ..._buildContent(context),
            const SizedBox(height: 20),
            Center(
              child: ElevatedButton.icon(
                icon: const Icon(Icons.open_in_new),
                label: const Text("Read Original"),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.green[700],
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                ),
                onPressed: () async {
                  final uri = Uri.tryParse(article.link);
                  if (uri != null && await canLaunchUrl(uri)) {
                    await launchUrl(uri, mode: LaunchMode.externalApplication);
                  } else {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text("Unable to open link")),
                    );
                  }
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}
