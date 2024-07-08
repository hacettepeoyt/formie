#[macro_use]
extern crate rocket;

mod proxy;

#[launch]
fn rocket() -> _ {
    rocket::build()
        .mount("/", proxy::ProxyHandler)
        .manage(proxy::SecondaryServer::new())
}
