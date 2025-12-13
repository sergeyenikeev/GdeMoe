package com.gdemo.ui.screens.review

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import coil.decode.VideoFrameDecoder
import coil.request.ImageRequest
import com.gdemo.data.model.AiDetectionDto
import com.gdemo.data.model.AiDetectionObjectDto
import com.gdemo.data.model.UploadHistoryEntryDto
import com.gdemo.data.remote.ApiClient
import com.gdemo.util.AnalyticsLogger

@Composable
fun AiReviewScreen(
    paddingValues: PaddingValues,
    viewModel: AiReviewViewModel,
    baseUrl: String,
    onOpenItem: (Int) -> Unit = {}
) {
    val uiState by viewModel.ui.collectAsState()
    val context = LocalContext.current
    var selectedTab by remember { mutableStateOf(0) }

    LaunchedEffect(selectedTab) {
        if (selectedTab == 1) {
            viewModel.refreshHistory()
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(paddingValues)
            .padding(12.dp)
    ) {
        Text("AI Review", style = MaterialTheme.typography.headlineSmall)
        TabRow(selectedTabIndex = selectedTab) {
            Tab(selected = selectedTab == 0, onClick = { selectedTab = 0 }) { Text("Queue") }
            Tab(selected = selectedTab == 1, onClick = { selectedTab = 1 }) { Text("History") }
        }
        Spacer(modifier = Modifier.height(8.dp))
        if (selectedTab == 0 && uiState.isLoading) {
            LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
        }
        if (selectedTab == 1 && uiState.isHistoryLoading) {
            LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
        }
        uiState.error?.let { Text("Error: $it", color = MaterialTheme.colorScheme.error) }
        if (selectedTab == 0) {
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                verticalArrangement = Arrangement.spacedBy(12.dp),
                contentPadding = PaddingValues(bottom = 24.dp)
            ) {
                items(uiState.items) { detection ->
                    DetectionCard(
                        detection = detection,
                        baseUrl = baseUrl,
                        onAccept = {
                            AnalyticsLogger.event("ai_review_accept", mapOf("detectionId" to detection.id))
                            viewModel.accept(detection.id)
                        },
                        onReject = {
                            AnalyticsLogger.event("ai_review_reject", mapOf("detectionId" to detection.id))
                            viewModel.reject(detection.id)
                        },
                        onOpenItem = onOpenItem,
                        onUpdateObject = { objId, itemId, locationId ->
                            viewModel.updateObject(objId, itemId, locationId, decision = "accepted")
                        },
                        onPlayVideo = { url ->
                            val intent = Intent(Intent.ACTION_VIEW).apply {
                                setDataAndType(Uri.parse(url), "video/*")
                                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                            }
                            context.startActivity(intent)
                        }
                    )
                }
            }
        } else {
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                verticalArrangement = Arrangement.spacedBy(12.dp),
                contentPadding = PaddingValues(bottom = 24.dp)
            ) {
                items(uiState.history) { entry ->
                    UploadHistoryCard(
                        entry = entry,
                        baseUrl = baseUrl,
                        onOpenItem = onOpenItem,
                        onUpdateObject = { objId, itemId, locationId ->
                            viewModel.updateObject(objId, itemId, locationId, decision = "accepted")
                        }
                    )
                }
            }
        }
    }
}

@Composable
private fun DetectionCard(
    detection: AiDetectionDto,
    baseUrl: String,
    onAccept: () -> Unit,
    onReject: () -> Unit,
    onOpenItem: (Int) -> Unit,
    onUpdateObject: (Int, Int?, Int?) -> Unit,
    onPlayVideo: (String) -> Unit
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text("Media #${detection.media_id} / ${detection.status}")
            DetectionMediaPreview(detection.media_path, baseUrl, onPlayVideo)
            detection.objects.take(3).forEach { obj ->
                DetectionRow(
                    obj = obj,
                    onOpenItem = onOpenItem,
                    onUpdate = { itemId, locationId -> onUpdateObject(obj.id, itemId, locationId) }
                )
            }
            if (detection.objects.size > 3) {
                Text("+ ${detection.objects.size - 3} more")
            }
            Spacer(Modifier.height(4.dp))
            RowActions(onAccept = onAccept, onReject = onReject)
        }
    }
}

@Composable
private fun UploadHistoryCard(
    entry: UploadHistoryEntryDto,
    baseUrl: String,
    onOpenItem: (Int) -> Unit,
    onUpdateObject: (Int, Int?, Int?) -> Unit
) {
    val context = LocalContext.current
    val sanitized = remember(baseUrl) { ApiClient.sanitizeBaseUrl(baseUrl).trimEnd('/') }
    val thumbUrl = remember(entry.thumb_url, entry.thumb_path, entry.file_url, entry.path) {
        entry.thumb_url?.let { sanitized + "/" + it.trimStart('/') }
            ?: entry.thumb_path?.let { sanitized + "/" + it.trimStart('/') }
            ?: entry.file_url?.let { sanitized + "/" + it.trimStart('/') }
            ?: entry.path?.let { sanitized + "/" + it.trimStart('/') }
    }
    val mediaUrl = remember(entry.file_url, entry.path) {
        entry.file_url?.let { sanitized + "/" + it.trimStart('/') }
            ?: entry.path?.let { sanitized + "/" + it.trimStart('/') }
    }
    val isVideo = (entry.media_type == "video") || (mediaUrl?.lowercase()?.endsWith(".mp4") == true)
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text("Upload #${entry.id}: ${entry.status}")
            Text("AI: ${entry.ai_status ?: "-"}")
            thumbUrl?.let { url ->
                val model: Any = if (isVideo) {
                    ImageRequest.Builder(context)
                        .data(url)
                        .decoderFactory(VideoFrameDecoder.Factory())
                        .build()
                } else url
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(180.dp)
                ) {
                    AsyncImage(
                        model = model,
                        contentDescription = null,
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(180.dp)
                            .clip(RoundedCornerShape(8.dp))
                    )
                    if (isVideo && mediaUrl != null) {
                        Icon(
                            imageVector = Icons.Default.PlayArrow,
                            contentDescription = null,
                            modifier = Modifier
                                .align(Alignment.Center)
                                .clickable {
                                    val intent = Intent(Intent.ACTION_VIEW).apply {
                                        setDataAndType(Uri.parse(mediaUrl), "video/*")
                                        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                                    }
                                    context.startActivity(intent)
                                }
                        )
                    }
                }
            }
            entry.objects.take(3).forEach { obj ->
                DetectionRow(
                    obj = obj,
                    onOpenItem = onOpenItem,
                    onUpdate = { itemId, locationId -> onUpdateObject(obj.id, itemId, locationId) }
                )
            }
            if (entry.objects.size > 3) {
                Text("+ ${entry.objects.size - 3} more")
            }
        }
    }
}

@Composable
private fun DetectionRow(
    obj: AiDetectionObjectDto,
    onOpenItem: (Int) -> Unit,
    onUpdate: ((Int?, Int?) -> Unit)? = null
) {
    var itemInput by remember(obj.id) { mutableStateOf(obj.linked_item_id?.toString() ?: "") }
    var locationInput by remember(obj.id) {
        mutableStateOf(obj.linked_location_id?.toString() ?: obj.suggested_location_id?.toString().orEmpty())
    }
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text("${obj.label} (${(obj.confidence * 100).toInt()}%)")
        obj.suggested_location_id?.let {
            Text("Suggested location: $it", style = MaterialTheme.typography.bodySmall)
        }
        if (obj.candidates.isNotEmpty()) {
            Text("Candidates:", style = MaterialTheme.typography.bodySmall)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                obj.candidates.forEach { c ->
                    val id = (c["item_id"] as? Number)?.toInt() ?: return@forEach
                    val score = (c["score"] as? Number)?.toDouble() ?: 0.0
                    Button(onClick = { onOpenItem(id) }) {
                        Text("#$id (${(score * 100).toInt()}%)")
                    }
                }
            }
        }
        if (obj.linked_item_id != null || obj.linked_location_id != null) {
            Text(
                "Linked: item=${obj.linked_item_id ?: "-"}, location=${obj.linked_location_id ?: "-"}",
                style = MaterialTheme.typography.bodySmall
            )
        }
        onUpdate?.let { updater ->
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = itemInput,
                    onValueChange = { itemInput = it },
                    label = { Text("Item ID") },
                    modifier = Modifier.weight(1f)
                )
                OutlinedTextField(
                    value = locationInput,
                    onValueChange = { locationInput = it },
                    label = { Text("Location ID") },
                    modifier = Modifier.weight(1f)
                )
            }
            Button(onClick = { updater(itemInput.toIntOrNull(), locationInput.toIntOrNull()) }) {
                Text("Save links")
            }
        }
    }
}

@Composable
private fun DetectionMediaPreview(
    mediaPath: String?,
    baseUrl: String,
    onPlay: (String) -> Unit
) {
    val context = LocalContext.current
    val url = remember(mediaPath, baseUrl) {
        mediaPath?.let { path ->
            val clean = path.trimStart('/')
            ApiClient.sanitizeBaseUrl(baseUrl).trimEnd('/') + "/" + clean
        }
    }
    val isVideo = remember(url) { url?.lowercase()?.endsWith(".mp4") == true }
    url?.let { mediaUrl ->
        val model: Any = if (isVideo) {
            ImageRequest.Builder(context)
                .data(mediaUrl)
                .decoderFactory(VideoFrameDecoder.Factory())
                .build()
        } else mediaUrl
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(180.dp)
        ) {
            AsyncImage(
                model = model,
                contentDescription = null,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(180.dp)
                    .clip(RoundedCornerShape(8.dp))
            )
            if (isVideo) {
                Icon(
                    imageVector = Icons.Default.PlayArrow,
                    contentDescription = null,
                    modifier = Modifier
                        .align(Alignment.Center)
                        .clickable { onPlay(mediaUrl) }
                )
            }
        }
    }
}

@Composable
private fun RowActions(onAccept: () -> Unit, onReject: () -> Unit) {
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Button(onClick = onAccept, modifier = Modifier.weight(1f)) { Text("Approve") }
        OutlinedButton(onClick = onReject, modifier = Modifier.weight(1f)) { Text("Reject") }
    }
}