package org.jellyfin.mobile.player.vlc

import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.view.WindowManager
import android.widget.Button
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.SeekBar
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import org.jellyfin.mobile.utils.Constants
import org.videolan.libvlc.LibVLC
import org.videolan.libvlc.Media
import org.videolan.libvlc.MediaPlayer
import org.videolan.libvlc.util.VLCVideoLayout

class InternalVlcPlayerActivity : AppCompatActivity() {

    private lateinit var libVLC: LibVLC
    private lateinit var mediaPlayer: MediaPlayer
    private lateinit var videoLayout: VLCVideoLayout
    private lateinit var playPause: Button
    private lateinit var seekBar: SeekBar
    private lateinit var positionText: TextView

    private var startPositionMs = 0L
    private var userSeeking = false
    private var returnedResult = false

    private val progressUpdater = object : Runnable {
        override fun run() {
            if (::mediaPlayer.isInitialized && !userSeeking) {
                val duration = mediaPlayer.length.coerceAtLeast(0L)
                val position = mediaPlayer.time.coerceAtLeast(0L)

                if (duration > 0L) {
                    seekBar.max = 1000
                    seekBar.progress =
                        ((position * 1000L) / duration)
                            .toInt()
                            .coerceIn(0, 1000)
                }

                positionText.text =
                    "${formatTime(position)} / ${formatTime(duration)}"
            }

            if (::seekBar.isInitialized) {
                seekBar.postDelayed(this, 500L)
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        window.addFlags(
            WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON
        )

        @Suppress("DEPRECATION")
        window.decorView.systemUiVisibility =
            View.SYSTEM_UI_FLAG_FULLSCREEN or
                View.SYSTEM_UI_FLAG_HIDE_NAVIGATION or
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY

        val mediaUri = intent.data

        if (mediaUri == null) {
            finishWithResult(false)
            return
        }

        startPositionMs =
            intent.getIntExtra("position", 0)
                .toLong()
                .coerceAtLeast(0L)

        buildUi()

        libVLC = LibVLC(
            this,
            arrayListOf(
                "--audio-time-stretch",
                "--network-caching=1500",
                "--http-reconnect",
            ),
        )

        mediaPlayer = MediaPlayer(libVLC)

        mediaPlayer.attachViews(
            videoLayout,
            null,
            false,
            false,
        )

        mediaPlayer.setEventListener { event ->
            runOnUiThread {
                when (event.type) {

                    MediaPlayer.Event.Playing -> {
                        if (
                            startPositionMs > 0L &&
                            mediaPlayer.time < 1000L
                        ) {
                            mediaPlayer.time = startPositionMs
                        }

                        playPause.text = "Pause"
                    }

                    MediaPlayer.Event.Paused -> {
                        playPause.text = "Play"
                    }

                    MediaPlayer.Event.EndReached -> {
                        finishWithResult(true)
                    }

                    MediaPlayer.Event.EncounteredError -> {
                        finishWithResult(false)
                    }
                }
            }
        }

        val media = Media(
            libVLC,
            mediaUri,
        )

        media.setHWDecoderEnabled(
            true,
            false,
        )

        media.addOption(
            ":network-caching=1500"
        )

        media.addOption(
            ":http-reconnect=true"
        )

        intent.getStringExtra(
            "subtitles_location"
        )
            ?.takeIf {
                it.isNotBlank()
            }
            ?.let { subtitle ->
                media.addSlave(
                    Media.Slave.Type.Subtitle,
                    subtitle,
                    true,
                )
            }

        mediaPlayer.media = media

        media.release()

        mediaPlayer.play()

        seekBar.post(
            progressUpdater
        )
    }

    private fun buildUi() {
        val root = FrameLayout(this).apply {
            setBackgroundColor(
                Color.BLACK
            )
        }

        videoLayout =
            VLCVideoLayout(this)

        root.addView(
            videoLayout,
            FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT,
            ),
        )

        val controls =
            LinearLayout(this).apply {
                orientation =
                    LinearLayout.HORIZONTAL

                gravity =
                    Gravity.CENTER_VERTICAL

                setPadding(
                    16,
                    8,
                    16,
                    8,
                )

                setBackgroundColor(
                    0x99000000.toInt()
                )
            }

        val back =
            Button(this).apply {
                text = "Voltar"

                setOnClickListener {
                    finishWithResult(false)
                }
            }

        playPause =
            Button(this).apply {
                text = "Pause"

                setOnClickListener {
                    if (mediaPlayer.isPlaying) {
                        mediaPlayer.pause()
                    } else {
                        mediaPlayer.play()
                    }
                }
            }

        seekBar =
            SeekBar(this).apply {
                max = 1000

                setOnSeekBarChangeListener(
                    object :
                        SeekBar.OnSeekBarChangeListener {

                        override fun onProgressChanged(
                            seekBar: SeekBar?,
                            progress: Int,
                            fromUser: Boolean,
                        ) = Unit

                        override fun onStartTrackingTouch(
                            seekBar: SeekBar?,
                        ) {
                            userSeeking = true
                        }

                        override fun onStopTrackingTouch(
                            seekBar: SeekBar?,
                        ) {
                            val duration =
                                mediaPlayer.length

                            if (
                                duration > 0L &&
                                seekBar != null
                            ) {
                                mediaPlayer.time =
                                    (
                                        duration *
                                            seekBar.progress
                                    ) / 1000L
                            }

                            userSeeking = false
                        }
                    }
                )
            }

        positionText =
            TextView(this).apply {
                setTextColor(
                    Color.WHITE
                )

                text =
                    "00:00 / 00:00"

                setPadding(
                    12,
                    0,
                    0,
                    0,
                )
            }

        controls.addView(
            back
        )

        controls.addView(
            playPause
        )

        controls.addView(
            seekBar,
            LinearLayout.LayoutParams(
                0,
                LinearLayout.LayoutParams.WRAP_CONTENT,
                1f,
            ),
        )

        controls.addView(
            positionText
        )

        root.addView(
            controls,
            FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.WRAP_CONTENT,
                Gravity.BOTTOM,
            ),
        )

        setContentView(
            root
        )
    }

    @Deprecated(
        "Deprecated in Java"
    )
    override fun onBackPressed() {
        finishWithResult(false)
    }

    private fun finishWithResult(
        ended: Boolean,
    ) {
        if (returnedResult) {
            return
        }

        returnedResult = true

        val position =
            if (::mediaPlayer.isInitialized) {
                mediaPlayer.time
                    .coerceAtLeast(0L)
            } else {
                0L
            }

        val duration =
            if (::mediaPlayer.isInitialized) {
                mediaPlayer.length
                    .coerceAtLeast(0L)
            } else {
                0L
            }

        val finalPosition =
            if (
                ended &&
                duration > 0L
            ) {
                duration
            } else {
                position
            }

        setResult(
            Activity.RESULT_OK,
            Intent(
                Constants.VLC_PLAYER_RESULT_ACTION
            ).apply {
                putExtra(
                    "extra_position",
                    finalPosition,
                )

                putExtra(
                    "extra_duration",
                    duration,
                )
            },
        )

        finish()
    }

    override fun onDestroy() {
        if (::seekBar.isInitialized) {
            seekBar.removeCallbacks(
                progressUpdater
            )
        }

        if (::mediaPlayer.isInitialized) {
            mediaPlayer.stop()

            mediaPlayer.detachViews()

            mediaPlayer.release()
        }

        if (::libVLC.isInitialized) {
            libVLC.release()
        }

        super.onDestroy()
    }

    private fun formatTime(
        ms: Long,
    ): String {
        val totalSeconds =
            ms.coerceAtLeast(0L) /
                1000L

        val hours =
            totalSeconds /
                3600L

        val minutes =
            (totalSeconds % 3600L) /
                60L

        val seconds =
            totalSeconds %
                60L

        return if (hours > 0L) {
            "%d:%02d:%02d".format(
                hours,
                minutes,
                seconds,
            )
        } else {
            "%02d:%02d".format(
                minutes,
                seconds,
            )
        }
    }
}
