; this is when it gets neat...

(import discord)
(import os)

(setq client ((. discord Client)))
(setq TOKEN ((. os getenv) "DISCORD_TOKEN"))

(defn on_message 'async (ctx)
    (setq msg (. ctx content))
    (setq chan (. ctx channel))
    (if (!= (. ctx author) (. client user))
        @(
            (if (= msg "!hello")
                (await ((. chan send) "Hello, World!"))
                nil)
        )
        nil))

(defn on_ready 'async () 
    (print "Ready.")))

((. client event) on_message)
((. client event) on_ready)

(print "Starting the bot...")
((. client run) TOKEN)