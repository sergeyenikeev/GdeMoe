package com.gdemo.ui.screens.media

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun MediaLinkScreen(paddingValues: PaddingValues) {
    Column(modifier = Modifier.padding(paddingValues).padding(16.dp)) {
        Text(text = "Привязка фото/видео к карточке и месту")
        Button(onClick = { /* TODO: open picker and upload */ }, modifier = Modifier.padding(top = 12.dp)) {
            Text("Загрузить медиа")
        }
    }
}
