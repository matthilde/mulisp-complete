; Mulisp REPL

(import readline)
(import cumiler)

(while true
    (setq cmd (input "lisp> "))
    (print (. cumiler parse_lisp)
)