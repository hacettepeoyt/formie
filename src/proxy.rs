use rocket::data::ToByteUnit;
use rocket::http::Method;
use rocket::response::Responder;
use rocket::route::Handler;
use rocket::route::Outcome;
use rocket::Data;
use rocket::Request;
use rocket::Route;

pub struct SecondaryServer {
    process: std::process::Child,
}

impl SecondaryServer {
    pub fn new() -> SecondaryServer {
        #[cfg(debug_assertions)]
        SecondaryServer {
            process: std::process::Command::new("/usr/bin/env")
                .args(if cfg!(debug_assertions) {
                    vec!["python", "-m", "flask", "run", "-p 5241"]
                } else {
                    vec![
                        "python",
                        "-m",
                        "gunicorn",
                        "--bind",
                        "127.0.0.1:5241",
                        "formie:create_app()",
                    ]
                })
                .spawn()
                .expect("Failed to start secondary server"),
        }
    }
}

impl Drop for SecondaryServer {
    fn drop(&mut self) {
        eprintln!("Cleaning up secondary server...");

        match self.process.try_wait() {
            Ok(Some(_)) => (),
            _ => {
                eprintln!("Sending sigterm to secondary server.");
                unsafe {
                    libc::kill(self.process.id() as i32, libc::SIGTERM);
                }
            }
        }

        let _ = self.process.wait();
    }
}

fn transform_method(method: rocket::http::Method) -> reqwest::Method {
    match method {
        rocket::http::Method::Get => reqwest::Method::GET,
        rocket::http::Method::Put => reqwest::Method::PUT,
        rocket::http::Method::Post => reqwest::Method::POST,
        rocket::http::Method::Delete => reqwest::Method::DELETE,
        rocket::http::Method::Options => reqwest::Method::OPTIONS,
        rocket::http::Method::Head => reqwest::Method::HEAD,
        rocket::http::Method::Trace => reqwest::Method::TRACE,
        rocket::http::Method::Connect => reqwest::Method::CONNECT,
        rocket::http::Method::Patch => reqwest::Method::PATCH,
    }
}

pub async fn upstream_request(
    uri: &str,
    method: reqwest::Method,
    req_ctx: &Request<'_>,
    body: Option<Data<'_>>,
) -> reqwest::Response {
    let client = reqwest::Client::builder()
        .redirect(reqwest::redirect::Policy::none())
        .build()
        .unwrap();

    let mut req_headers = reqwest::header::HeaderMap::new();
    for h in req_ctx.headers().clone().iter() {
        req_headers.insert(
            reqwest::header::HeaderName::from_bytes(h.name.as_str().as_bytes()).unwrap(),
            h.value().parse().unwrap(),
        );
    }

    client
        .request(method, format!("http://127.0.0.1:5241{}", uri))
        .headers(req_headers)
        .body(if body.is_some() {
            body.unwrap()
                .open(8.mebibytes())
                .into_bytes()
                .await
                .unwrap()
                .value
        } else {
            vec![]
        }) // TODO: stream this
        .send()
        .await
        .unwrap()
}

struct WrappedResponse<'r>(rocket::response::Result<'r>);

impl WrappedResponse<'_> {
    async fn from<'r>(req: &'r Request<'_>, data: Data<'r>) -> WrappedResponse<'r> {
        let res = upstream_request(
            &format!("{}", req.uri()),
            transform_method(req.method()),
            req,
            Some(data),
        )
        .await;
        let mut res2 = rocket::response::Response::build();
        res2.status(rocket::http::Status {
            code: res.status().as_u16(),
        });

        for (k, v) in res.headers().clone() {
            if let (Some(key), Ok(value)) = (k, v.to_str()) {
                res2.raw_header(key.as_str().to_owned(), value.to_owned());
            }
        }

        // TODO: stream this
        let data = res.bytes().await.unwrap();

        WrappedResponse(res2.sized_body(data.len(), std::io::Cursor::new(data)).ok())
    }
}

#[rocket::async_trait]
impl<'r> Responder<'r, 'r> for WrappedResponse<'r> {
    fn respond_to(self, _: &'r Request<'_>) -> rocket::response::Result<'r> {
        self.0
    }
}

#[derive(Clone)]
pub struct ProxyHandler;

#[rocket::async_trait]
impl Handler for ProxyHandler {
    async fn handle<'r>(&self, req: &'r Request<'_>, data: Data<'r>) -> Outcome<'r> {
        Outcome::from(req, WrappedResponse::from(req, data).await)
    }
}

#[allow(clippy::from_over_into)]
impl Into<Vec<Route>> for ProxyHandler {
    fn into(self) -> Vec<Route> {
        vec![
            Route::new(Method::Get, "/<paths...>", self.clone()),
            Route::new(Method::Post, "/<paths...>", self),
        ]
    }
}
