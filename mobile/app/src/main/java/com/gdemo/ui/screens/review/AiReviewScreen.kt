package com.gdemo.ui.screens.review

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.gdemo.data.model.AiDetectionDto
import com.gdemo.data.model.AiDetectionObjectDto

@Composable
fun AiReviewScreen(
    paddingValues: PaddingValues,
    viewModel: AiReviewViewModel
) {
    val uiState by viewModel.ui.collectAsState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(paddingValues)
            .padding(12.dp)
    ) {
        Text("AI-предложения", style = MaterialTheme.typography.headlineSmall)
        Spacer(modifier = Modifier.height(8.dp))
        if (uiState.isLoading) {
            LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
        }
        uiState.error?.let { Text("Ошибка: $it", color = MaterialTheme.colorScheme.error) }
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            verticalArrangement = Arrangement.spacedBy(12.dp),
            contentPadding = PaddingValues(bottom = 24.dp)
        ) {
            items(uiState.items) { detection ->
                DetectionCard(
                    detection = detection,
                    onAccept = { viewModel.accept(detection.id) },
                    onReject = { viewModel.reject(detection.id) }
                )
            }
        }
    }
}

@Composable
private fun DetectionCard(
    detection: AiDetectionDto,
    onAccept: () -> Unit,
    onReject: () -> Unit
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text("Media #${detection.media_id} — ${detection.status}")
            detection.objects.take(3).forEach { obj ->
                DetectionRow(obj)
            }
            if (detection.objects.size > 3) {
                Text("+ ещё ${detection.objects.size - 3}")
            }
            Spacer(Modifier.height(4.dp))
            RowActions(onAccept = onAccept, onReject = onReject)
        }
    }
}

@Composable
private fun DetectionRow(obj: AiDetectionObjectDto) {
    Column {
        Text("${obj.label} (${(obj.confidence * 100).toInt()}%)")
        obj.suggested_location_id?.let {
            Text("Локация: $it", style = MaterialTheme.typography.bodySmall)
        }
        if (obj.candidates.isNotEmpty()) {
            Text(
                "Кандидаты: " + obj.candidates.joinToString { c -> "${c["item_id"]}:${c["score"]}" },
                style = MaterialTheme.typography.bodySmall
            )
        }
    }
}

@Composable
private fun RowActions(onAccept: () -> Unit, onReject: () -> Unit) {
    androidx.compose.foundation.layout.Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Button(onClick = onAccept, modifier = Modifier.weight(1f)) { Text("Принять") }
        OutlinedButton(onClick = onReject, modifier = Modifier.weight(1f)) { Text("Отклонить") }
    }
}
