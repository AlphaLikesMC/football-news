import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../models/news.dart';
import '../utils/custom_cache_manager.dart';

class NewsDetailPage extends StatelessWidget {
  final News article;

  const NewsDetailPage({super.key, required this.article});

  List<Widget> _buildContent(BuildContext context) {
    final widgets = <Widget>[];
    final text =
        article.content ?? article.description ?? "No content available";

    final parts = text.split(RegExp(r"\s+"));
    final buffer = StringBuffer();

    for (final word in parts) {
      if (word.startsWith("http")) {
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
          widgets.add(
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: CachedNetworkImage(
                imageUrl: word,
                cacheManager: CustomCacheManager.instance,
                width: double.infinity,
                fit: BoxFit.contain,
                placeholder: (context, url) =>
                    Container(height: 220, color: Colors.grey[300]),
                errorWidget: (context, url, error) => Container(
                  height: 220,
                  color: Colors.grey[300],
                  child: const Icon(Icons.broken_image),
                ),
              ),
            ),
          );
        } else {
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

  String _sourceFromLink(String? link) {
    if (link == null || link.isEmpty) return 'Source';
    try {
      final host = Uri.parse(link).host;
      if (host.isEmpty) return 'Source';
      return host.replaceFirst('www.', '');
    } catch (e) {
      return 'Source';
    }
  }

  @override
  Widget build(BuildContext context) {
    final heroTag = article.image ?? article.title;
    final hasImage = article.image != null && article.image!.trim().isNotEmpty;
    final sourceText = _sourceFromLink(article.link);

    return Scaffold(
      backgroundColor: Colors.grey[100],
      body: SafeArea(
        child: Column(
          children: [
            // top visual with back/share
            SizedBox(
              height: 280,
              child: Stack(
                children: [
                  Positioned.fill(
                    child: Hero(
                      tag: heroTag,
                      child: hasImage
                          ? CachedNetworkImage(
                              imageUrl: article.image!,
                              cacheManager: CustomCacheManager.instance,
                              fit: BoxFit.cover,
                              placeholder: (c, u) =>
                                  Container(color: Colors.grey[300]),
                              errorWidget: (c, u, e) => Container(
                                color: Colors.grey[300],
                                child: const Icon(Icons.broken_image),
                              ),
                            )
                          : Container(
                              color: Colors.grey[300],
                              child: const Icon(Icons.image_not_supported),
                            ),
                    ),
                  ),
                  Positioned.fill(
                    child: Container(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          colors: [
                            Colors.transparent,
                            Colors.black.withOpacity(0.45),
                          ],
                          begin: Alignment.topCenter,
                          end: Alignment.bottomCenter,
                        ),
                      ),
                    ),
                  ),
                  Positioned(
                    left: 12,
                    top: 12,
                    child: CircleAvatar(
                      backgroundColor: Colors.black.withOpacity(0.4),
                      child: IconButton(
                        icon: const Icon(Icons.arrow_back, color: Colors.white),
                        onPressed: () => Navigator.of(context).pop(),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      article.title,
                      style: Theme.of(context).textTheme.headlineSmall
                          ?.copyWith(fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 6,
                          ),
                          decoration: BoxDecoration(
                            color: Colors.green.shade50,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Text(
                            sourceText,
                            style: TextStyle(color: Colors.green.shade800),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Text(
                          "${article.publishedAt.toLocal()}".split(" ")[0],
                          style: TextStyle(color: Colors.grey[600]),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    ..._buildContent(context),
                    const SizedBox(height: 20),
                    Center(
                      child: ElevatedButton.icon(
                        icon: const Icon(Icons.open_in_new),
                        label: const Text("Read Original"),
                        onPressed: () async {
                          final uri = Uri.tryParse(article.link);
                          if (uri != null && await canLaunchUrl(uri)) {
                            await launchUrl(
                              uri,
                              mode: LaunchMode.externalApplication,
                            );
                          } else {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(
                                content: Text("Unable to open link"),
                              ),
                            );
                          }
                        },
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
